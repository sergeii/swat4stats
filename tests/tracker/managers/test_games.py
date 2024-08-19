import pytest

from apps.tracker.entities import CoopRank
from apps.tracker.models import Game


@pytest.mark.parametrize(
    "score, expected_rank",
    [
        (-41, CoopRank.menace),
        (0, CoopRank.menace),
        (1, CoopRank.menace),
        (19, CoopRank.menace),
        (20, CoopRank.vigilante),
        (34, CoopRank.vigilante),
        (35, CoopRank.washout),
        (49, CoopRank.washout),
        (50, CoopRank.recruit),
        (59, CoopRank.recruit),
        (60, CoopRank.non_sworn_officer),
        (69, CoopRank.non_sworn_officer),
        (70, CoopRank.reserve_officer),
        (74, CoopRank.reserve_officer),
        (75, CoopRank.patrol_officer),
        (79, CoopRank.patrol_officer),
        (80, CoopRank.sergeant),
        (84, CoopRank.sergeant),
        (85, CoopRank.lieutenant),
        (89, CoopRank.lieutenant),
        (90, CoopRank.captain),
        (94, CoopRank.captain),
        (95, CoopRank.inspector),
        (99, CoopRank.inspector),
        (100, CoopRank.chief_inspector),
        (101, CoopRank.chief_inspector),
        (150, CoopRank.chief_inspector),
    ],
)
def test_calculate_coop_rank_for_score(score: int, expected_rank: CoopRank) -> None:
    assert Game.objects.calculate_coop_rank_for_score(score) == expected_rank
