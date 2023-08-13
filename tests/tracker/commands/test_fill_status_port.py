from django.core.management import call_command

from tests.factories.tracker import ServerFactory


def test_fill_status_port(db):
    svr1 = ServerFactory(ip="1.1.1.1", port=10480, status_port=None)
    svr2 = ServerFactory(ip="1.1.1.2", port=10580, status_port=10581)
    svr3 = ServerFactory(ip="1.1.1.3", port=10480, status_port=10484)
    svr4 = ServerFactory(ip="1.1.1.4", port=10880, status_port=0)

    call_command("fill_status_port")

    for s in [svr1, svr2, svr3, svr4]:
        s.refresh_from_db()

    assert svr1.status_port == 10481
    assert svr2.status_port == 10581
    assert svr3.status_port == 10484
    assert svr4.status_port == 10881
