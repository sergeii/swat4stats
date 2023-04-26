from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.tracker.factories import (ProfileFactory, LoadoutFactory, PlayerFactory)
from apps.tracker.tasks import update_player_preferences, update_player_preferences_for_profile
from apps.utils.test import freeze_timezone_now


@pytest.mark.django_db(databases=['default', 'replica'])
@mock.patch.object(update_player_preferences_for_profile, 'apply_async',
                   wraps=update_player_preferences_for_profile.apply_async)
def test_update_player_preferences(task_mock, django_assert_num_queries):
    now = timezone.now()
    old_loadout = LoadoutFactory(primary='9mm SMG', secondary='Taser Stun Gun')
    new_loadout = LoadoutFactory(primary='Suppressed 9mm SMG', secondary='9mm Handgun')

    broken_profile = ProfileFactory(last_seen_at=None, first_seen_at=None)
    PlayerFactory.create_batch(3, alias__name='BrokenPlayer', alias__profile=broken_profile, alias__isp__country='eu',
                               loadout=new_loadout, team='suspects')

    old_profile = ProfileFactory(loadout=old_loadout,
                                 name='Player',
                                 country='eu',
                                 team='swat',
                                 preferences_updated_at=now - timedelta(days=1),
                                 first_seen_at=now - timedelta(days=10),
                                 last_seen_at=now - timedelta(days=10))
    PlayerFactory.create_batch(3, alias__name='NewPlayer', alias__profile=old_profile, alias__isp__country='un',
                               loadout=new_loadout, team='suspects')

    new_profile = ProfileFactory(loadout=old_loadout,
                                 name='Mekanos',
                                 country='nl',
                                 team='suspects',
                                 preferences_updated_at=now - timedelta(days=2),
                                 first_seen_at=now - timedelta(days=1),
                                 last_seen_at=now - timedelta(days=1))
    PlayerFactory.create_batch(3, alias__name='Mek', alias__profile=new_profile, alias__isp__country='nl',
                               loadout=new_loadout, team='suspects')

    another_profile = ProfileFactory(loadout=old_loadout,
                                     name='Konten',
                                     country='nl',
                                     team='swat',
                                     preferences_updated_at=None,
                                     first_seen_at=now - timedelta(days=1),
                                     last_seen_at=now - timedelta(days=1))
    PlayerFactory.create_batch(3, alias__name='Konten', alias__profile=another_profile, alias__isp__country='nl',
                               loadout=LoadoutFactory(), team='suspects')

    with freeze_timezone_now(now), django_assert_num_queries(15):
        update_player_preferences.delay()

    assert task_mock.called
    updated_pks = {call[1]['args'][0] for call in task_mock.call_args_list}
    assert updated_pks == {new_profile.pk, another_profile.pk}

    broken_profile.refresh_from_db()
    assert broken_profile.name is None
    assert broken_profile.country is None
    assert broken_profile.team is None
    assert broken_profile.loadout is None
    assert broken_profile.preferences_updated_at is None

    old_profile.refresh_from_db()
    assert old_profile.name == 'Player'
    assert old_profile.country == 'eu'
    assert old_profile.team == 'swat'
    assert old_profile.loadout == old_loadout
    assert old_profile.preferences_updated_at == now - timedelta(days=1)

    new_profile.refresh_from_db()
    assert new_profile.name == 'Mek'
    assert new_profile.country == 'nl'
    assert new_profile.team == 'suspects'
    assert new_profile.loadout == new_loadout
    assert new_profile.preferences_updated_at == now

    another_profile.refresh_from_db()
    assert another_profile.name == 'Konten'
    assert another_profile.country == 'nl'
    assert another_profile.team == 'suspects'
    assert another_profile.loadout == LoadoutFactory()
    assert another_profile.preferences_updated_at == now
