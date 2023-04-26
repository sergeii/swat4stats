from datetime import datetime

import pytest
from pytz import UTC

from apps.tracker.exceptions import MergeServersError
from apps.tracker.factories import ServerFactory, GameFactory
from apps.tracker.models import Server, Game
from apps.utils.test import freeze_timezone_now


def test_merge_servers(db):
    server1, server2, server3 = ServerFactory.create_batch(3)

    games1 = GameFactory.create_batch(2, server=server1)
    games2 = GameFactory.create_batch(3, server=server2)

    now = datetime(2023, 5, 1, 23, 0, 0, tzinfo=UTC)

    with freeze_timezone_now(now):
        Server.objects.merge_servers(main=server2, merged=[server1, server3])

    for server in [server1, server2, server3]:
        server.refresh_from_db()

    assert server2.enabled
    assert server2.merged_into is None
    assert server2.merged_into_at is None

    assert not server1.enabled
    assert server1.merged_into.pk == server2.pk
    assert server1.merged_into_at == now
    assert server1.merged_stats_at is None

    assert not server3.enabled
    assert server3.merged_into.pk == server2.pk
    assert server3.merged_into_at == now
    assert server3.merged_stats_at is None

    for game in Game.objects.filter(pk__in=[g.pk for g in games1 + games2]):
        assert game.server.pk == server2.pk


def test_merge_servers_in_sequence(db):
    server1, server2, server3, server4 = ServerFactory.create_batch(4)

    games1 = GameFactory.create_batch(2, server=server1)
    games2 = GameFactory.create_batch(2, server=server2)
    games3 = GameFactory.create_batch(2, server=server3)

    now = datetime(2023, 5, 1, 23, 0, 0, tzinfo=UTC)
    with freeze_timezone_now(now):
        Server.objects.merge_servers(main=server2, merged=[server3])

    for server in [server1, server2, server3, server4]:
        server.refresh_from_db()

    # not yet merged
    assert server1.enabled
    assert server1.merged_into is None
    assert server1.merged_into_at is None

    assert server2.enabled
    assert server2.merged_into is None
    assert server2.merged_into_at is None

    # just merged
    assert not server3.enabled
    assert server3.merged_into.pk == server2.pk
    assert server3.merged_into_at == now

    # not yet merged
    assert server4.enabled
    assert server4.merged_into is None
    assert server4.merged_into_at is None

    for game in Game.objects.filter(pk__in=[g.pk for g in games2 + games3]):
        assert game.server.pk == server2.pk

    for game in Game.objects.filter(pk__in=[g.pk for g in games1]):
        assert game.server.pk == server1.pk

    then = datetime(2023, 5, 2, 23, 5, 0, tzinfo=UTC)
    with freeze_timezone_now(then):
        Server.objects.merge_servers(main=server1, merged=[server2, server4])

    for server in [server1, server2, server3, server4]:
        server.refresh_from_db()

    assert server1.enabled
    assert server1.merged_into is None
    assert server1.merged_into_at is None

    assert not server2.enabled
    assert server2.merged_into.pk == server1.pk
    assert server2.merged_into_at == then

    assert not server3.enabled
    assert server3.merged_into.pk == server1.pk
    assert server3.merged_into_at == now

    assert not server4.enabled
    assert server4.merged_into.pk == server1.pk
    assert server4.merged_into_at == then

    for game in Game.objects.filter(pk__in=[g.pk for g in games1 + games2 + games3]):
        assert game.server.pk == server1.pk


def test_merge_servers_no_games(db):
    server1, server2 = ServerFactory.create_batch(2)

    now = datetime(2023, 5, 1, 23, 0, 0, tzinfo=UTC)
    with freeze_timezone_now(now):
        Server.objects.merge_servers(main=server2, merged=[server1])

    for server in [server1, server2]:
        server.refresh_from_db()

    assert not server1.enabled
    assert server1.merged_into.pk == server2.pk
    assert server1.merged_into_at == now

    assert server2.enabled
    assert server2.merged_into is None


def test_cant_merge_no_servers(db):
    server = ServerFactory()

    with pytest.raises(MergeServersError):
        Server.objects.merge_servers(main=server, merged=[])


@pytest.mark.parametrize('with_extra_servers', [True, False])
def test_cant_merge_server_with_itself(db, with_extra_servers):
    server = ServerFactory()
    merged_servers = [server]

    if with_extra_servers:
        merged_servers += ServerFactory.create_batch(2)

    with pytest.raises(MergeServersError):
        Server.objects.merge_servers(main=server, merged=[server])

    assert Server.objects.filter(merged_into__isnull=False).count() == 0


def test_cant_merge_to_server_that_is_merged(db):
    server1, server2 = ServerFactory.create_batch(2)
    main = ServerFactory(merged_into=ServerFactory())

    with pytest.raises(MergeServersError):
        Server.objects.merge_servers(main=main, merged=[server1])

    for server in [server1, server2]:
        server.refresh_from_db()
        assert server.enabled
        assert server.merged_into is None


@pytest.mark.parametrize('with_extra_servers', [True, False])
def test_cant_merge_to_servers_that_are_merged(db, with_extra_servers):
    server = ServerFactory(merged_into=ServerFactory())
    main = ServerFactory()

    merged_servers = [server]
    if with_extra_servers:
        merged_servers += ServerFactory.create_batch(2)

    with pytest.raises(MergeServersError):
        Server.objects.merge_servers(main=main, merged=merged_servers)


@pytest.mark.parametrize('to_same_server', [True, False])
def test_cant_merge_all_merged_servers(db, to_same_server):
    if to_same_server:
        servers = ServerFactory.create_batch(3, merged_into=ServerFactory())
    else:
        servers = [ServerFactory(merged_into=ServerFactory()) for _ in range(3)]

    with pytest.raises(MergeServersError):
        Server.objects.merge_servers(main=servers[0], merged=servers[1:])


def test_cant_merge_servers_twice(db):
    server1, server2 = ServerFactory.create_batch(2)
    main = ServerFactory()

    now = datetime(2023, 5, 1, 23, 0, 0, tzinfo=UTC)
    with freeze_timezone_now(now):
        Server.objects.merge_servers(main=main, merged=[server1, server2])

    for server in [server1, server2]:
        server.refresh_from_db()
        assert not server.enabled
        assert server.merged_into == main
        assert server.merged_into_at == now

    then = datetime(2023, 5, 2, 23, 5, 0, tzinfo=UTC)
    with pytest.raises(MergeServersError), freeze_timezone_now(then):
        Server.objects.merge_servers(main=main, merged=[server1])

    for server in [server1, server2]:
        assert server.merged_into == main
        assert server.merged_into_at == now
