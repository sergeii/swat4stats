import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from django.db import models, transaction
from django.db.models import Q, Exists, OuterRef
from django.db.models.functions import window

from apps.tracker.entities import LegacyStatCategory
from apps.utils.misc import iterate_list

if TYPE_CHECKING:
    from apps.tracker.models import Profile  # noqa


logger = logging.getLogger(__name__)


class StatsManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('profile')

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

    def rank(self, *,
             year: int,
             cats: list[str] = None,
             exclude_cats: list[str] = None,
             qualify: dict[str, int | float] = None) -> None:
        filters = Q()

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

        logger.info('have %s %s items to update positions for %s', cnt, self.model._meta.model_name, year)

        for category, positions in positions_per_cat.items():
            logger.debug('updating %s positions for %s - %s', year, self.model._meta.model_name, category)
            with transaction.atomic():
                # clear positions prior to updating when qualifications are specified
                if qualify:
                    logger.debug('clearing %s positions for %s - %s', year, self.model._meta.model_name, category)
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
