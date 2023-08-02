import logging
from collections import defaultdict
from datetime import datetime, time
from typing import TYPE_CHECKING, Any

from django.db import models, transaction
from django.db.models import Q, F, Exists, OuterRef
from django.db.models.functions import window
from django.utils import timezone
from pytz import UTC

from apps.tracker.entities import LegacyStatCategory
from apps.utils.misc import iterate_list, concat_it

if TYPE_CHECKING:
    from apps.tracker.models import Profile  # noqa


logger = logging.getLogger(__name__)


def get_stats_period_for_year(year: int) -> tuple[datetime, datetime]:
    jan_1st = datetime(year=year, month=1, day=1, tzinfo=UTC)
    moment_before_new_year = datetime.combine(
        datetime(year=year, month=12, day=31),  # noqa: DTZ001
        time.max,
    ).replace(tzinfo=UTC)
    return jan_1st, moment_before_new_year


class StatsManager(models.Manager):

    def save_stats(
        self,
        items: dict[str, int | float],
        *,
        profile: 'Profile',
        year: int,
        **save_kwargs: Any,
    ) -> None:
        from apps.tracker.models import PlayerStats  # noqa

        batch = []

        for category, points in items.items():
            # skip zero or negative points
            if not points or points <= 0:
                continue

            if issubclass(self.model, PlayerStats):
                save_kwargs['category_legacy'] = getattr(LegacyStatCategory, category)

            batch.append(
                self.model(
                    profile=profile,
                    category=category,
                    points=points,
                    year=year,
                    **save_kwargs
                )
            )

        if not batch:
            return

        self.model.objects.bulk_create(
            batch,
            batch_size=500,
            update_conflicts=True,
            update_fields=['points'],
            unique_fields=self.model.unique_db_fields,
        )

    def save_grouped_stats(
        self,
        grouped_items: dict[str, dict[str, int | float]],
        *,
        grouping_key: str,
        profile: 'Profile',
        year: int,
    ) -> None:
        for grouping_value, items in grouped_items.items():
            self.save_stats(items,
                            profile=profile,
                            year=year,
                            **{grouping_key: grouping_value})

    def rank(
        self,
        *,
        year: int,
        cats: list[str] = None,
        exclude_cats: list[str] = None,
        qualify: dict[str, int | float] = None,
        filters: dict[str, Any] = None,
    ) -> None:
        filters = Q(**filters) if filters else Q()

        if cats:
            filters &= Q(category__in=cats)
        elif exclude_cats:
            filters &= ~Q(category__in=exclude_cats)

        # only rank those players that are qualified for it
        # i.e. that have enough time and games played
        if qualify is not None:
            extra_ref_fields = [
                f for f in self.model.grouping_fields  # map_id, gametype, server_id, etc
                if f not in ('category', 'category_legacy')
            ]
            filters &= Q(*(
                Exists(self.model.objects.using('replica')
                       .filter(profile_id=OuterRef('profile_id'),
                               year=year,
                               category=ref_category,
                               points__gte=min_points,
                               **{field: OuterRef(field) for field in extra_ref_fields}))
                for ref_category, min_points in qualify.items()
            ))

        positions_qs = (
            self.model.objects
            .using('replica')
            .filter(filters, year=year)
            .annotate(
                _position=models.Window(
                    expression=window.RowNumber(),
                    partition_by=[models.F(field) for field in self.model.grouping_fields],
                    order_by=[models.F('points').desc(), models.F('id').asc()],
                )
            )
            .values('pk', 'category', '_position')
        )

        positions_per_cat = defaultdict(list)
        cnt = 0
        for item in positions_qs:
            cnt += 1
            positions_per_cat[item['category']].append((item['pk'], item['_position']))

        logger.info('have %s %s items to update positions for year %s', cnt, self.model._meta.model_name, year)

        for category, positions in positions_per_cat.items():
            logger.debug('updating year %s positions for %s - %s', year, self.model._meta.model_name, category)
            with transaction.atomic(durable=True):
                # clear positions prior to updating when qualifications are specified
                if qualify:
                    logger.debug('clearing year %s positions for %s - %s', year, self.model._meta.model_name, category)
                    (self.model.objects
                     .filter(year=year, category=category, position__isnull=False)
                     .update(position=None))
                for chunk in iterate_list(positions, size=1000):
                    position_for = dict(chunk)
                    chunk_qs = (self.model.objects
                                .select_related(None)
                                .filter(pk__in=position_for)
                                .only('pk', 'position'))
                    for item in chunk_qs:
                        item.position = position_for[item.pk]
                    self.model.objects.bulk_update(chunk_qs, ['position'])


class ServerStatsManager(StatsManager):

    def merge_unmerged_stats(self) -> None:
        from apps.tracker.models import Server, Profile
        # collect the servers that have been merged into other servers
        # and have not merged stats yet
        merged_servers_pairs = (
            Server.objects.using('replica')
            .filter(Q(merged_into__isnull=False),
                    Q(merged_stats_at__isnull=True) | Q(merged_stats_at__lt=F('merged_into_at')))
            .values_list('id', 'merged_into_id', named=True)
        )
        merged_servers = {
            item.id: item.merged_into_id
            for item in merged_servers_pairs
        }

        if not merged_servers:
            logger.info('no servers to merge stats for')
            return

        # find all stats that belong to merged servers
        # grouped by profile and year
        unmerged_stats_summary = (
            self.using('replica')
            .filter(server__in=merged_servers)
            .order_by('server_id', 'profile_id', 'year')
            .distinct('server_id', 'profile_id', 'year')
            .values('server_id', 'profile_id', 'year')
        )

        affected_servers_per_year: dict[int, set[int]] = defaultdict(set)
        affected_profiles_per_server: dict[int, set[tuple[int, int]]] = defaultdict(set)
        # collect all yearly profiles affected by the merge, grouped by main server
        for item in unmerged_stats_summary:
            main_server_id = merged_servers[item['server_id']]
            affected_profiles_per_server[main_server_id].add((item['profile_id'], item['year']))
            affected_servers_per_year[item['year']].add(main_server_id)

        # recalculate profile stats individually for each main server
        for main_server_id, affected_profiles in affected_profiles_per_server.items():
            self._recalculate_merged_stats_for_server(
                main_server_id=main_server_id,
                affected_profiles=affected_profiles,
            )

        # recalculate server stats positions for each affected year
        for year in sorted(affected_servers_per_year):
            affected_servers = affected_servers_per_year[year]
            logger.info('updating server stats positions for year %s', year)
            Profile.objects.update_per_server_positions_for_year(year=year,
                                                                 filters={'server__in': affected_servers})

        # mark merged servers as having merged stats
        # and delete the obsolete server stats
        self._delete_merged_stats_for_servers(list(merged_servers))

    @transaction.atomic(durable=True)
    def _recalculate_merged_stats_for_server(
        self,
        *,
        main_server_id: int,
        affected_profiles: set[tuple[int, int]],
    ) -> None:
        from apps.tracker.models import Profile, Server

        main_server = Server.objects.using('replica').get(id=main_server_id)
        profiles = (Profile.objects.using('replica')
                    .in_bulk(id_list=[profile_id for profile_id, _ in affected_profiles]))

        logger.info('calculating merged stats for server %d of %d annual profiles',
                    main_server_id, len(affected_profiles))

        for profile_id, year in affected_profiles:
            Profile.objects.update_annual_server_stats_for_profile(
                profile=profiles[profile_id],
                server=main_server,
                year=year,
                no_savepoint=True,
            )

    @transaction.atomic(durable=True)
    def _delete_merged_stats_for_servers(self, merged_server_ids: list[int]) -> None:
        from apps.tracker.models import Server

        merged_server_ids_str = concat_it(merged_server_ids)
        # mark the merged servers as having stats merged
        logger.info('marking %d merged servers as having stats merged: %s',
                    len(merged_server_ids), merged_server_ids_str)
        Server.objects.filter(id__in=merged_server_ids).update(merged_stats_at=timezone.now())

        # delete servers stats items for merged servers
        logger.info('deleting annual stats for %d merged servers: %s', len(merged_server_ids), merged_server_ids_str)
        delete_qs = self.filter(server_id__in=merged_server_ids)
        deleted_rows_cnt = delete_qs._raw_delete(using=delete_qs.db)
        logger.info('deleted %d annual stats for merged servers: %s', deleted_rows_cnt, merged_server_ids_str)
