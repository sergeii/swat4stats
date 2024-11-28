from datetime import datetime, timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from pytz import UTC

from apps.utils.test import freeze_timezone_now
from tests.factories.tracker import ServerFactory


@pytest.mark.django_db(databases=["default", "replica"])
@freeze_timezone_now(datetime(2023, 4, 18, 13, 1, 45, tzinfo=UTC))
def test_fill_clean_hostnames(now_mock, db, django_assert_num_queries):
    now = timezone.now()
    yesterday = now - timedelta(days=1)

    myt = ServerFactory(
        hostname="-==MYT Team Svr==-", hostname_clean=None, hostname_updated_at=None
    )
    sef = ServerFactory(
        hostname="[c=0099ff]SEF BTLA 1.6 EU",
        hostname_clean="SEF BTLA 1.6 EU",
        hostname_updated_at=yesterday,
    )
    sog = ServerFactory(
        hostname="[c=4169e1]Sog-team.co.uk [c=00c500]P[c=00DB00]r[c=22FF22]o[C=6fff6f]!",
        hostname_clean=None,
        hostname_updated_at=None,
    )
    empty_str = ServerFactory(hostname="", hostname_clean=None, hostname_updated_at=None)
    null = ServerFactory(hostname=None, hostname_clean=None, hostname_updated_at=None)

    with django_assert_num_queries(6):
        call_command("fill_clean_hostnames")

    for server in [myt, sef, sog, empty_str, null]:
        server.refresh_from_db()

    assert myt.hostname_clean == "-==MYT Team Svr==-"
    assert myt.hostname_updated_at == now

    # this server already has a clean hostname, so it should not be updated
    assert sef.hostname_clean == "SEF BTLA 1.6 EU"
    assert sef.hostname_updated_at == yesterday

    assert sog.hostname_clean == "Sog-team.co.uk Pro!"
    assert sog.hostname_updated_at == now

    # server with empty hostname should also have an empty clean hostname
    assert empty_str.hostname_clean == ""
    assert empty_str.hostname_updated_at == now

    # these servers have no hostname, so they should not be updated
    assert null.hostname_clean is None
    assert null.hostname_updated_at is None
