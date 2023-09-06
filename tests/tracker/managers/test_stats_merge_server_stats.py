from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tracker.models import ServerStats
from apps.utils.test import freeze_timezone_now
from tests.factories.stats import ServerStatsFactory
from tests.factories.tracker import (
    GameFactory,
    PlayerFactory,
    ProfileFactory,
    ServerFactory,
)


@pytest.fixture
def now():
    return timezone.now()


@pytest.mark.django_db(databases=["default", "replica"])
def test_merge_unmerged_server_stats_happy_flow(now, settings, django_assert_num_queries):
    settings.TRACKER_MIN_GAMES = 3

    then = now + timedelta(seconds=5)
    dt2020 = now.replace(year=2020)
    dt2021 = now.replace(year=2021)

    profile1, profile2, profile3, profile4, profile5 = ProfileFactory.create_batch(5)

    server1 = ServerFactory()
    server2 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(days=1))
    server3 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(days=3))
    # nobody played on server4, hence no stats merged
    server4 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(hours=1))
    server5 = ServerFactory()

    # in 2020, player 1 played on all 3 servers + 1 more totally unrelated server
    PlayerFactory(
        alias__profile=profile1,
        game=GameFactory(date_finished=dt2020, server=server1),
        score=100,
        kills=75,
    )
    PlayerFactory(
        alias__profile=profile1,
        game=GameFactory(date_finished=dt2020, server=server1),  # formerly server2
        score=1000,
        kills=1000,
    )
    PlayerFactory(
        alias__profile=profile1,
        game=GameFactory(date_finished=dt2020, server=server1),  # formerly server3
        score=-50,
        kills=0,
    )
    PlayerFactory(
        alias__profile=profile1,
        game=GameFactory(date_finished=dt2020, server=server5),
        score=10,
        kills=5,
    )
    ServerStatsFactory(
        category="score", year=2020, server=server1, profile=profile1, points=100, position=1
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server1, profile=profile1, points=75, position=1
    )
    ServerStatsFactory(
        category="score", year=2020, server=server2, profile=profile1, points=1000, position=2
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server2, profile=profile1, points=1000, position=1
    )
    ServerStatsFactory(
        category="score", year=2020, server=server3, profile=profile1, points=-50, position=2
    )
    ServerStatsFactory(
        category="score", year=2020, server=server5, profile=profile1, points=10, position=3
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server5, profile=profile1, points=5, position=3
    )

    # in 2020, player 2 played on main server only
    PlayerFactory(
        alias__profile=profile2,
        game=GameFactory(date_finished=dt2020, server=server1),
        score=10,
        kills=1,
        arrests=5,
    )
    # incorrect stats for player 2 on server2 on purpose
    ServerStatsFactory(
        category="score", year=2020, server=server1, profile=profile2, points=1, position=1
    )
    ServerStatsFactory(
        category="games", year=2020, server=server1, profile=profile2, points=10, position=2
    )

    # in 2020, player 3 played on one of merged servers
    PlayerFactory(
        alias__profile=profile3,
        game=GameFactory(date_finished=dt2020, server=server1),  # formerly server2
        score=100,
        kills=90,
    )
    ServerStatsFactory(
        category="score", year=2020, server=server2, profile=profile3, points=100, position=3
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server2, profile=profile3, points=90, position=2
    )

    # in 2020, player 4 played on both merged servers
    PlayerFactory(
        alias__profile=profile4,
        game=GameFactory(date_finished=dt2020, server=server1),  # formerly server2
        score=1010,
        kills=950,
    )
    PlayerFactory(
        alias__profile=profile4,
        game=GameFactory(date_finished=dt2020, server=server1),  # formerly server3
        score=-2,
        kills=1,
    )
    ServerStatsFactory(
        category="score", year=2020, server=server2, profile=profile4, points=1010, position=1
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server2, profile=profile4, points=950, position=2
    )
    ServerStatsFactory(
        category="score", year=2020, server=server3, profile=profile4, points=-2, position=1
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server3, profile=profile4, points=1, position=1
    )

    # in 2020, player 5 played on unrelated server
    PlayerFactory(
        alias__profile=profile5,
        game=GameFactory(date_finished=dt2020, server=server5),
        score=955,
        kills=950,
        arrests=1,
    )
    ServerStatsFactory(
        category="score", year=2020, server=server5, profile=profile5, points=955, position=2
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server5, profile=profile5, points=950, position=2
    )

    # in 2021, some players played on main server only
    PlayerFactory(
        alias__profile=profile1,
        game=GameFactory(date_finished=dt2021, server=server1),
        score=150,
        kills=125,
    )
    PlayerFactory(
        alias__profile=profile2,
        game=GameFactory(date_finished=dt2021, server=server1),
        score=175,
        kills=150,
    )
    PlayerFactory(
        alias__profile=profile3,
        game=GameFactory(date_finished=dt2021, server=server1),
        score=10,
        kills=15,
    )

    ServerStatsFactory(
        category="score", year=2021, server=server1, profile=profile1, points=150, position=2
    )
    ServerStatsFactory(
        category="kills", year=2021, server=server1, profile=profile1, points=125, position=2
    )

    ServerStatsFactory(
        category="score", year=2021, server=server1, profile=profile2, points=175, position=1
    )
    ServerStatsFactory(
        category="kills", year=2021, server=server1, profile=profile2, points=150, position=1
    )

    ServerStatsFactory(
        category="score", year=2021, server=server1, profile=profile3, points=10, position=3
    )
    ServerStatsFactory(
        category="kills", year=2021, server=server1, profile=profile3, points=15, position=4
    )

    with django_assert_num_queries(37), freeze_timezone_now(then):
        ServerStats.objects.merge_unmerged_stats()

    assert ServerStats.objects.filter(server=server1, year=2020).count() == 14
    assert ServerStats.objects.filter(server=server2, year=2020).count() == 0
    assert ServerStats.objects.filter(server=server3, year=2020).count() == 0
    assert ServerStats.objects.filter(server=server4, year=2020).count() == 0
    assert ServerStats.objects.filter(server=server5, year=2020).count() == 4

    assert (
        ServerStats.objects.get(
            server=server1, profile=profile1, category="score", year=2020
        ).points
        == 1050
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile1, category="kills", year=2020
        ).points
        == 1075
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile1, category="spr_ratio", year=2020
        ).points
        == 350
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile1, category="games", year=2020
        ).points
        == 3
    )
    assert (
        ServerStats.objects.get(
            server=server5, profile=profile1, category="score", year=2020
        ).points
        == 10
    )
    assert (
        ServerStats.objects.get(
            server=server5, profile=profile1, category="kills", year=2020
        ).points
        == 5
    )

    # stats of player 2 are not recalculated, because he played only on main server
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile2, category="score", year=2020
        ).points
        == 1
    )
    assert (
        ServerStats.objects.filter(
            server=server1, profile=profile2, category="kills", year=2020
        ).count()
        == 0
    )
    assert (
        ServerStats.objects.filter(
            server=server1, profile=profile2, category="spr_ratio", year=2020
        ).count()
        == 0
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile2, category="games", year=2020
        ).points
        == 10
    )

    assert (
        ServerStats.objects.get(
            server=server1, profile=profile3, category="score", year=2020
        ).points
        == 100
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile3, category="kills", year=2020
        ).points
        == 90
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile3, category="spr_ratio", year=2020
        ).points
        == 100
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile3, category="games", year=2020
        ).points
        == 1
    )

    assert (
        ServerStats.objects.get(
            server=server1, profile=profile4, category="score", year=2020
        ).points
        == 1008
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile4, category="kills", year=2020
        ).points
        == 951
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile4, category="spr_ratio", year=2020
        ).points
        == 504
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile4, category="games", year=2020
        ).points
        == 2
    )

    assert (
        ServerStats.objects.get(
            server=server5, profile=profile5, category="score", year=2020
        ).points
        == 955
    )
    assert (
        ServerStats.objects.get(
            server=server5, profile=profile5, category="kills", year=2020
        ).points
        == 950
    )

    # positions are updated
    assert list(
        ServerStats.objects.filter(server=server1, category="score", year=2020)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile1.id, 1), (profile4.id, 2), (profile3.id, 3), (profile2.id, 4)]

    assert list(
        ServerStats.objects.filter(server=server1, category="kills", year=2020)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile1.id, 1), (profile4.id, 2), (profile3.id, 3)]

    assert list(
        ServerStats.objects.filter(server=server1, category="spr_ratio", year=2020)
        .order_by("position", "profile_id")
        .values_list("profile_id", "position")
    ) == [(profile1.id, 1), (profile3.id, None), (profile4.id, None)]

    assert list(
        ServerStats.objects.filter(server=server1, category="games", year=2020)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile2.id, 1), (profile1.id, 2), (profile4.id, 3), (profile3.id, 4)]

    for s in [server1, server2, server3]:
        s.refresh_from_db()
    assert server1.merged_stats_at is None
    assert server2.merged_stats_at == then
    assert server3.merged_stats_at == then

    # positions are unaffected for server 5
    assert list(
        ServerStats.objects.filter(server=server5, category="score", year=2020)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile5.id, 2), (profile1.id, 3)]
    assert list(
        ServerStats.objects.filter(server=server5, category="kills", year=2020)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile5.id, 2), (profile1.id, 3)]

    # stats for 2021 are not affected because they are not merged
    assert ServerStats.objects.filter(server=server1, year=2021).count() == 6
    assert ServerStats.objects.filter(server=server2, year=2021).count() == 0
    assert ServerStats.objects.filter(server=server3, year=2021).count() == 0
    assert ServerStats.objects.filter(server=server4, year=2021).count() == 0
    assert ServerStats.objects.filter(server=server5, year=2021).count() == 0

    assert (
        ServerStats.objects.get(
            server=server1, profile=profile1, category="score", year=2021
        ).points
        == 150
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile1, category="kills", year=2021
        ).points
        == 125
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile2, category="score", year=2021
        ).points
        == 175
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile2, category="kills", year=2021
        ).points
        == 150
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile3, category="score", year=2021
        ).points
        == 10
    )
    assert (
        ServerStats.objects.get(
            server=server1, profile=profile3, category="kills", year=2021
        ).points
        == 15
    )

    assert list(
        ServerStats.objects.filter(server=server1, category="score", year=2021)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile2.id, 1), (profile1.id, 2), (profile3.id, 3)]
    assert list(
        ServerStats.objects.filter(server=server1, category="kills", year=2021)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile2.id, 1), (profile1.id, 2), (profile3.id, 4)]

    # because the stats are now merged, consecutive calls to merge_unmerged_stats() do nothing
    with django_assert_num_queries(1):
        ServerStats.objects.merge_unmerged_stats()


@pytest.mark.django_db(databases=["default", "replica"])
def test_no_servers_were_merged(now, django_assert_num_queries):
    dt2020 = now.replace(year=2020)

    profile1, profile2, profile3 = ProfileFactory.create_batch(3)

    server1, server2, server3 = ServerFactory.create_batch(3)

    PlayerFactory(
        alias__profile=profile1,
        game=GameFactory(date_finished=dt2020, server=server1),
        score=100,
        kills=75,
    )
    PlayerFactory(
        alias__profile=profile2,
        game=GameFactory(date_finished=dt2020, server=server2),
        score=1000,
        kills=1000,
    )
    PlayerFactory(
        alias__profile=profile3,
        game=GameFactory(date_finished=dt2020, server=server2),
        score=-50,
        kills=0,
    )

    ServerStatsFactory(
        category="score", year=2020, server=server1, profile=profile1, points=100, position=1
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server1, profile=profile1, points=75, position=1
    )
    ServerStatsFactory(
        category="score", year=2020, server=server2, profile=profile2, points=1000, position=2
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server2, profile=profile2, points=1000, position=1
    )
    ServerStatsFactory(
        category="score", year=2020, server=server2, profile=profile3, points=-50, position=2
    )

    with django_assert_num_queries(1):
        ServerStats.objects.merge_unmerged_stats()

    assert ServerStats.objects.count() == 5
    assert ServerStats.objects.filter(server=server1).count() == 2
    assert ServerStats.objects.filter(server=server2).count() == 3


@pytest.mark.django_db(databases=["default", "replica"])
def test_no_server_no_server_stats():
    ServerStats.objects.merge_unmerged_stats()
    assert ServerStats.objects.count() == 0


@pytest.mark.django_db(databases=["default", "replica"])
def test_no_server_stats_to_merge(now, django_assert_num_queries):
    then = now + timedelta(seconds=5)
    dt2020 = now.replace(year=2020)

    profile1, profile2 = ProfileFactory.create_batch(2)

    server1 = ServerFactory()
    server2 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(days=1))
    server3 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(days=3))
    server4 = ServerFactory()

    PlayerFactory(
        alias__profile=profile1,
        game=GameFactory(date_finished=dt2020, server=server4),
        score=-50,
        kills=0,
    )

    PlayerFactory(
        alias__profile=profile2,
        game=GameFactory(date_finished=dt2020, server=server4),
        score=1000,
        kills=1000,
    )

    ServerStatsFactory(
        category="score", year=2020, server=server4, profile=profile1, points=-50, position=3
    )
    ServerStatsFactory(
        category="score", year=2020, server=server4, profile=profile2, points=1000, position=2
    )

    with django_assert_num_queries(6), freeze_timezone_now(then):
        ServerStats.objects.merge_unmerged_stats()

    for s in [server1, server2, server3, server4]:
        s.refresh_from_db()

    assert server1.merged_stats_at is None
    assert server2.merged_stats_at == then
    assert server3.merged_stats_at == then
    assert server4.merged_stats_at is None

    assert ServerStats.objects.count() == 2
    assert ServerStats.objects.filter(server=server4).count() == 2
    assert list(
        ServerStats.objects.filter(server=server4, category="score", year=2020)
        .order_by("position")
        .values_list("profile_id", "position")
    ) == [(profile2.id, 2), (profile1.id, 3)]

    # because the servers are marked as having stats merged,
    # consecutive calls to merge_unmerged_stats() do nothing
    with django_assert_num_queries(1), freeze_timezone_now(then + timedelta(minutes=10)):
        ServerStats.objects.merge_unmerged_stats()

    for s in [server1, server2, server3, server4]:
        s.refresh_from_db()

    assert server2.merged_stats_at == then
    assert server3.merged_stats_at == then


@pytest.mark.django_db(databases=["default", "replica"])
def test_server_stats_already_merged(now, django_assert_num_queries):
    then = now + timedelta(seconds=5)

    server1 = ServerFactory()
    server2 = ServerFactory(
        merged_into=server1,
        merged_into_at=now - timedelta(days=1),
        merged_stats_at=now - timedelta(hours=1),
    )
    server3 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(days=1))
    server4 = ServerFactory(
        merged_into=server1,
        merged_into_at=now - timedelta(days=1),
        merged_stats_at=now - timedelta(days=7),
    )

    ServerStatsFactory(category="score", year=2020, server=server1, points=100, position=1)

    with django_assert_num_queries(6), freeze_timezone_now(then):
        ServerStats.objects.merge_unmerged_stats()

    for s in [server1, server2, server3, server4]:
        s.refresh_from_db()

    assert server1.merged_stats_at is None
    assert server2.merged_stats_at == now - timedelta(hours=1)
    assert server3.merged_stats_at == then
    assert server4.merged_stats_at == then

    with django_assert_num_queries(1), freeze_timezone_now(then + timedelta(minutes=10)):
        ServerStats.objects.merge_unmerged_stats()

    for s in [server1, server2, server3, server4]:
        s.refresh_from_db()

    assert server1.merged_stats_at is None
    assert server2.merged_stats_at == now - timedelta(hours=1)
    assert server3.merged_stats_at == then
    assert server4.merged_stats_at == then


@pytest.mark.django_db(databases=["default", "replica"])
def test_stats_are_merged_but_not_deleted(now):
    then = now + timedelta(seconds=5)
    dt2020 = now.replace(year=2020)

    profile = ProfileFactory()

    server1 = ServerFactory()
    server2 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(days=1))
    server3 = ServerFactory(merged_into=server1, merged_into_at=now - timedelta(days=1))

    PlayerFactory(
        alias__profile=profile, game=GameFactory(date_finished=dt2020, server=server1), kills=1
    )
    PlayerFactory(
        alias__profile=profile, game=GameFactory(date_finished=dt2020, server=server1), kills=1000
    )

    ServerStatsFactory(
        category="kills", year=2020, server=server1, profile=profile, points=1001, position=None
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server2, profile=profile, points=1, position=1
    )
    ServerStatsFactory(
        category="kills", year=2020, server=server3, profile=profile, points=1000, position=1
    )

    with freeze_timezone_now(then):
        ServerStats.objects.merge_unmerged_stats()

    for s in [server1, server2, server3]:
        s.refresh_from_db()

    assert server1.merged_stats_at is None
    assert server2.merged_stats_at == then
    assert server3.merged_stats_at == then

    assert ServerStats.objects.count() == 2
    assert (
        ServerStats.objects.get(
            server=server1, category="kills", year=2020, profile=profile, position=1
        ).points
        == 1001
    )
    assert (
        ServerStats.objects.get(
            server=server1, category="games", year=2020, profile=profile, position=1
        ).points
        == 2
    )
