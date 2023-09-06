from apps.tracker.tasks import merge_servers
from tests.factories.tracker import GameFactory, ServerFactory


def test_merge_servers_task(db):
    main_server = ServerFactory()
    main_games = GameFactory.create_batch(2, server=main_server)

    other_server = ServerFactory()
    other_games = GameFactory.create_batch(2, server=other_server)

    merge_servers.delay(main_server.pk, [other_server.pk])

    main_server.refresh_from_db()
    other_server.refresh_from_db()

    assert main_server.enabled
    assert main_server.merged_into is None
    assert main_server.merged_into_at is None

    for g in main_games + other_games:
        g.refresh_from_db()
        assert g.server == main_server

    assert other_server.merged_into == main_server
    assert not other_server.enabled
