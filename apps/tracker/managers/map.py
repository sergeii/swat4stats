import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models, transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.text import slugify

if TYPE_CHECKING:
    from apps.tracker.models import Game, Map


logger = logging.getLogger(__name__)


class MapManager(models.Manager):
    def obtain_for(self, name: str) -> "Map":
        obj, _ = self.get_or_create(
            name=name,
            defaults={
                "slug": slugify(name),
            },
        )
        return obj

    def update_game_stats_with_game(self, game: "Game") -> None:
        update_qs = self.filter(pk=game.map_id)

        first_game_update_qs = update_qs.filter(first_game__isnull=True)
        last_game_update_qs = update_qs.filter(~Q(latest_game=game.pk))

        with transaction.atomic():
            first_game_update_qs.update(first_game=game, first_game_played_at=game.date_finished)
            last_game_update_qs.update(
                game_count=F("game_count") + 1,
                latest_game=game,
                latest_game_played_at=game.date_finished,
            )

    def update_ratings(self, chunk_size: int = 1000) -> None:
        maps_with_rating = self._get_maps_with_rating()

        logger.info("updating rating for %d maps", len(maps_with_rating))

        maps_to_update_qs = self.only("pk", "rating")
        for map_to_update in maps_to_update_qs:
            map_to_update.rating = maps_with_rating.get(map_to_update.pk)

        with transaction.atomic():
            self.bulk_update(maps_to_update_qs, ["rating"], batch_size=chunk_size)
            self.update(rating_updated_at=timezone.now())

    def _get_maps_with_rating(self) -> dict[int, int]:
        from apps.tracker.models import Game, Map

        finished_since = timezone.now() - timedelta(seconds=settings.TRACKER_MAP_RATINGS_FOR_PERIOD)
        game_stats_per_server = (
            Game.objects.using("replica")
            .filter(date_finished__gte=finished_since)
            .order_by("map")
            .values("map")
            .annotate(game_cnt=Count("pk"))
        )
        game_count_per_server_id = {row["map"]: row["game_cnt"] for row in game_stats_per_server}

        warehouse_map = Map.objects.using("replica").get(name="-EXP- Stetchkov Warehouse")
        maps_with_rating = (
            Map.objects.using("replica").filter(pk__in=game_count_per_server_id).only("pk", "name")
        )
        maps_sorted_by_rating = sorted(
            maps_with_rating,
            key=lambda m: (
                # vanilla maps first
                m.pk > warehouse_map.pk,
                # tss immediately after vanilla
                m.name.startswith("-EXP-"),
                # all maps other than tss and vanilla, sort by games played
                -game_count_per_server_id[m.pk] if m.pk > warehouse_map.pk else 0,
                m.name,
            ),
        )
        return {m.pk: idx for idx, m in enumerate(maps_sorted_by_rating, start=1)}

    @transaction.atomic
    def denorm_game_stats(self, *maps) -> None:
        from apps.tracker.models import Game

        map_ids = [m.pk for m in maps]
        game_stats_for_maps = (
            Game.objects.filter(map_id__in=map_ids)
            .order_by("map_id")
            .values("map_id")
            .annotate(
                game_count=models.Count("pk"),
                first_game_id=models.Min("pk"),
                latest_game_id=models.Max("pk"),
            )
        )

        game_stats_per_map_id: dict[int, dict] = {}
        game_ids: set[int] = set()
        for stats in game_stats_for_maps:
            game_stats_per_map_id[stats["map_id"]] = stats
            game_ids.add(stats["first_game_id"])
            game_ids.add(stats["latest_game_id"])

        min_max_games_qs = Game.objects.filter(pk__in=game_ids).values("pk", "date_finished")
        date_played_per_game_id = {row["pk"]: row["date_finished"] for row in min_max_games_qs}

        for game_map in maps:
            if stats := game_stats_per_map_id.get(game_map.pk):
                game_map.game_count = stats["game_count"]
                game_map.first_game_id = stats["first_game_id"]
                game_map.first_game_played_at = date_played_per_game_id.get(stats["first_game_id"])
                game_map.latest_game_id = stats["latest_game_id"]
                game_map.latest_game_played_at = date_played_per_game_id.get(
                    stats["latest_game_id"]
                )
            else:
                game_map.game_count = 0
                game_map.first_game_id = None
                game_map.first_game_played_at = None
                game_map.latest_game_id = None
                game_map.latest_game_played_at = None

        self.bulk_update(
            maps,
            [
                "game_count",
                "first_game_id",
                "first_game_played_at",
                "latest_game_id",
                "latest_game_played_at",
            ],
        )
