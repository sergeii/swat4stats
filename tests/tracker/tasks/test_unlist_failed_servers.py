from apps.tracker.tasks import unlist_failed_servers
from tests.factories.tracker import ServerFactory


def test_unlist_failed_servers(db, django_assert_num_queries, redis, settings):
    settings.TRACKER_STATUS_TOLERATED_FAILURES = 5

    ok_server = ServerFactory(ip="10.20.30.40", port=10480, failures=4, listed=True)
    offline_server1 = ServerFactory(ip="10.20.30.40", port=10580, failures=5, listed=True)
    offline_server2 = ServerFactory(ip="1.2.3.4", port=10480, failures=20, listed=True)
    offline_server3 = ServerFactory(ip="4.3.2.1", port=10580, failures=20, listed=True)
    already_unlisted_server = ServerFactory(ip="2.2.2.2", port=10480, failures=20, listed=False)

    redis.hmset(
        "servers",
        {
            "4.3.2.1:10580": "{}",  # should be deleted
            "10.20.30.40:10480": "{}",  # should stay
            "10.20.30.40:10580": "{}",  # should be deleted
            "10.20.30.40:10680": "{}",  # leftover from some other server, not deleted
            "2.2.2.2:10480": "{}",  # should stay because it's already unlisted
        },
    )

    with django_assert_num_queries(2):
        unlist_failed_servers.delay()

    assert set(redis.hgetall("servers")) == {
        b"10.20.30.40:10480",
        b"10.20.30.40:10680",
        b"2.2.2.2:10480",
    }

    for server in [
        ok_server,
        offline_server1,
        offline_server2,
        offline_server3,
        already_unlisted_server,
    ]:
        server.refresh_from_db()

    assert ok_server.listed is True
    assert offline_server1.listed is False
    assert offline_server2.listed is False
    assert offline_server3.listed is False
    assert already_unlisted_server.listed is False

    # it's safe to call the task again
    with django_assert_num_queries(1):
        unlist_failed_servers.delay()


def test_unlist_failed_servers_no_servers(db, django_assert_num_queries):
    with django_assert_num_queries(1):
        unlist_failed_servers.delay()
