from __future__ import unicode_literals

import datetime
import random
import socket

from cacheops import invalidation
from mock import patch, PropertyMock
from django import test
from django.core import exceptions
from django.utils import timezone
from django.db import connection, IntegrityError

from tracker import models, utils, const
from tracker.definitions import STAT


class TestCase(test.TestCase):

    def setUp(self):
        invalidation.invalidate_all()


class ServerTestCase(TestCase):

    valid_port_values = (1, '2', 1023, '1024', 10468, 24511, 65535)
    invalid_port_values = (-1000, -1, '0', 0, 65536, 100000)

    def test_create_server_valid_port_number(self):
        for port in self.valid_port_values:
            models.Server.objects.create_server('127.0.0.1', port)

    def test_create_server_invalid_port_number(self):
        for port in self.invalid_port_values:
            with self.assertRaises(exceptions.ValidationError):
                models.Server.objects.create_server('127.0.0.1', port)

    def test_create_server_duplicate_raises_exception(self):
        models.Server.objects.create(ip='127.0.0.1', port=10480)
        with self.assertRaises(exceptions.ValidationError):
            models.Server.objects.create_server('127.0.0.1', 10480)

    def test_server_manager_create_doesnt_raise_exception_on_valid_port_number(self):
        for port in self.valid_port_values:
            models.Server.objects.create(ip='127.0.0.1', port=port)

    def test_server_manager_create_raises_validation_error_on_invalid_port_number(self):
        for port in self.invalid_port_values:
            with self.assertRaises(exceptions.ValidationError):
                models.Server.objects.create(ip='127.0.0.1', port=port)

    def test_server_instance_save_raises_validation_error_on_invalid_port_number(self):
        instance = models.Server.objects.create(ip='127.0.0.1', port=10480)

        for port in self.invalid_port_values:
            with self.assertRaises(exceptions.ValidationError):
                instance.port = port
                instance.save()


class LoadoutTestCase(TestCase):

    def setUp(self):
        super(LoadoutTestCase, self).setUp()
        self.dict = {
            'primary': 0,
            'secondary': 0,
            'primary_ammo': 0,
            'secondary_ammo': 0,
            'head': 0,
            'body': 0,
            'equip_one': 0,
            'equip_two': 0,
            'equip_three': 0,
            'equip_four': 0,
            'equip_five': 0,
            'breacher': 0,
        }

    def test_loadout_get_or_create_will_return_none_if_all_items_are_missing(self):
        entry, created = models.Loadout.objects.get_or_create(**self.dict)
        self.assertIs(entry, None)
        self.assertFalse(created)

    def test_loadout_get_or_create_will_raise_an_exception_if_field_missing(self):
        self.dict.pop('primary')
        with self.assertRaises(AssertionError):
            models.Loadout.objects.get_or_create(**self.dict)


class RankTestCase(TestCase):

    def setUp(self):
        super(RankTestCase, self).setUp()
        self.profiles = (
            models.Profile.objects.create(),
            models.Profile.objects.create(),
            models.Profile.objects.create(),
            models.Profile.objects.create(),
        )

        self.year = 2014

        self.cats = (
            STAT.SCORE,
            STAT.TIME,
            STAT.SPM,
            STAT.SPR,
            STAT.GAMES,
        )

    def test_challenge_existing_profile_same_board(self):
        attrs = {
            'category': STAT.SCORE, 'year': self.year, 'profile': self.profiles[0]
        }

        models.Rank.objects.store(points=77, **attrs)
        self.assertEqual(models.Rank.objects.get(**attrs).points, 77)

        models.Rank.objects.store(points=78, **attrs)
        self.assertEqual(models.Rank.objects.get(**attrs).points, 78)

        self.assertEqual(models.Rank.objects.count(), 1)

    def test_challenge_existing_profile_different_board(self):
        for cat in self.cats:
            models.Rank.objects.store(cat, self.year, self.profiles[0], 77)
        self.assertEqual(models.Rank.objects.count(), len(self.cats))

        another_year = self.year - 10
        # another period, same categories
        for cat in self.cats:
            models.Rank.objects.store(cat, another_year, self.profiles[0], 77)
        self.assertEqual(models.Rank.objects.count(), len(self.cats)*2)

    def test_challenge_leaves_position_null(self):
        for cat in self.cats:
            attrs = {'category': cat, 'year': self.year, 'profile': self.profiles[0], 'points': 77}
            models.Rank.objects.store(**attrs)
            self.assertIs(models.Rank.objects.get(**attrs).position, None)

    def test_challenge_with_zero_points_removes_existing_entry(self):
        pass


class RankCacheTestCase(TestCase):

    def setUp(self):
        super(RankCacheTestCase, self).setUp()
        self.profiles = (
            models.Profile.objects.create(),
            models.Profile.objects.create(),
            models.Profile.objects.create(),
            models.Profile.objects.create(),
            models.Profile.objects.create(),
        )

        self.year = 2014

        models.Rank.objects.store(STAT.TIME, self.year, self.profiles[0], 1023)
        models.Rank.objects.store(STAT.TIME, self.year, self.profiles[1], 475)
        models.Rank.objects.store(STAT.TIME, self.year, self.profiles[2], 1575)
        models.Rank.objects.store(STAT.TIME, self.year, self.profiles[3], 2575)
        models.Rank.objects.store(STAT.TIME, self.year, self.profiles[4], 6575)

        models.Rank.objects.store(STAT.SCORE, self.year, self.profiles[0], 452)
        models.Rank.objects.store(STAT.SCORE, self.year, self.profiles[1], 473)
        models.Rank.objects.store(STAT.SCORE, self.year, self.profiles[2], 21)

    def test_rank__cache_same_score_sorts_by_id(self):
        for profile in self.profiles:
            models.Rank.objects.store(STAT.SPM, self.year, profile, 77)

        models.Rank.objects.rank(self.year)

        for i, profile in enumerate(self.profiles):
            self.assertEqual(models.Rank.objects.get(category=STAT.SPM, profile=profile.pk).position, i+1)

    def test_rank_cache_stores_positions_year(self):
        another_year = self.year - 13

        models.Rank.objects.store(STAT.TIME, another_year, self.profiles[0], 1123)
        models.Rank.objects.store(STAT.TIME, another_year, self.profiles[1], 2457)
        models.Rank.objects.store(STAT.TIME, another_year, self.profiles[2], 9827)
        models.Rank.objects.store(STAT.TIME, another_year, self.profiles[3], 4571)
        models.Rank.objects.store(STAT.TIME, another_year, self.profiles[4], 2524)

        models.Rank.objects.rank(self.year)

        self.assertEqual(models.Rank.objects.get(points=1023).position, 4)
        self.assertEqual(models.Rank.objects.get(points=475).position, 5)
        self.assertEqual(models.Rank.objects.get(points=1575).position, 3)
        self.assertEqual(models.Rank.objects.get(points=2575).position, 2)
        self.assertEqual(models.Rank.objects.get(points=6575).position, 1)

        self.assertEqual(models.Rank.objects.get(points=452).position, 2)
        self.assertEqual(models.Rank.objects.get(points=473).position, 1)
        self.assertEqual(models.Rank.objects.get(points=21).position, 3)

        self.assertEqual(models.Rank.objects.get(points=1123).position, None)
        self.assertEqual(models.Rank.objects.get(points=2457).position, None)
        self.assertEqual(models.Rank.objects.get(points=9827).position, None)
        self.assertEqual(models.Rank.objects.get(points=4571).position, None)
        self.assertEqual(models.Rank.objects.get(points=2524).position, None)


class PlayerForeignFieldsTestCase(TestCase):

    def setUp(self):
        super(PlayerForeignFieldsTestCase, self).setUp()
        self.test_profile = models.Profile.objects.create()
        self.test_alias = models.Alias.objects.create(profile=self.test_profile, name='Serge')
        self.test_game = models.Game.objects.create()

    def test_delete_related_loadout_sets_null(self):
        loadout = models.Loadout.objects.create()
        player = models.Player.objects.create(
            game=self.test_game, alias=self.test_alias, loadout=loadout, ip='127.0.0.1'
        )
        self.assertEqual(models.Player.objects.get(pk=player.pk).loadout.pk, loadout.pk)

        loadout.delete()
        self.assertIs(models.Player.objects.get(pk=player.pk).loadout, None)

    def test_delete_related_alias_removes_the_player_oncascade(self):
        player = models.Player.objects.create(
            game=self.test_game, alias=self.test_alias, ip='127.0.0.1'
        )
        self.assertIs(models.Player.objects.get(pk=player.pk).alias.pk, self.test_alias.pk)

        self.test_alias.delete()
        self.assertRaises(exceptions.ObjectDoesNotExist, models.Player.objects.get, pk=player.pk)

    def test_delete_related_game_removes_the_player_oncascade(self):
        player = models.Player.objects.create(
            game=self.test_game, alias=self.test_alias, ip='127.0.0.1'
        )

        self.assertIs(models.Player.objects.get(pk=player.pk).game.pk, self.test_game.pk)
        self.test_game.delete()
        self.assertRaises(exceptions.ObjectDoesNotExist, models.Player.objects.get, pk=player.pk)

    def test_delete_related_profile_removes_the_player_oncascade(self):
        player = models.Player.objects.create(
            game=self.test_game, alias=self.test_alias, ip='127.0.0.1'
        )

        self.assertIs(models.Player.objects.get(pk=player.pk).alias.profile.pk, self.test_profile.pk)
        self.test_profile.delete()
        self.assertRaises(exceptions.ObjectDoesNotExist, models.Player.objects.get, pk=player.pk)


class ISPTestCase(TestCase):

    invalid_whois_results = (
        {'country': 'un', 'orgname': 'foo'},
        {'country': 'un', 'orgname': 'foo', 'ipv4range': None},
        {'country': 'un', 'orgname': 'foo', 'ipv4range': ('foo', 'bar', 'ham')}, # 3-tuple
        {'country': 'un', 'orgname': 'foo', 'ipv4range': ('127.0.0.0', '625.255.255.255')},
    )

    valid_whois_results = (
        {'foo': 'bar', 'ipv4range': ('127.0.0.0', '127.255.255.255')},
        {'country': None, 'orgname': None, 'ipv4range': ('127.255.0.0', '127.255.255.255')},
        {'country': 'un', 'orgname': None, 'ipv4range': ('127.255.255.0', '127.255.255.255')},
        {'country': None, 'orgname': 'localhost', 'ipv4range': ('127.128.0.0', '127.255.255.255')},
        {'country': 'un', 'orgname': 'localhost', 'ipv4range': ('127.255.128.0', '127.255.255.255')},
        {'country': 'un', 'orgname': 'localhost', 'ipv4range': ('127.0.0.1', '127.0.0.1')},
        {'country': 'cn', 'orgname': 'SXTY-ZhenYi-NETBAR', 'ipv4range': ('59.49.78.131', '59.49.78.131')},
    )

    invalid_ranges = (
        ('foo', 'bar'),
        ('127.0.0.2', '127.0.0.1'),
        ('127.0.0.255', '127.0.0.0'),
        ('0.0.0.0', '255.255.255.256'),
    )

    def test_exceptions_raised_by_whois_are_ignored(self):
        for effect in (socket.timeout, TypeError, ValueError, UnicodeDecodeError):
            with patch('tracker.models.whois.whois', side_effect=effect) as mock:
                obj, created = models.ISP.objects.match_or_create('127.0.0.1')
                self.assertFalse(created)
                self.assertIs(obj, None)

                self.assertEqual(models.ISP.objects.count(), 0)
                self.assertEqual(models.IP.objects.count(), 0)

    def test_invalid_results_returned_by_whois_are_ignored(self):
        for invalid_ret_val in self.invalid_whois_results:
            with patch('tracker.models.whois.whois', return_value=invalid_ret_val):
                obj, created = models.ISP.objects.match_or_create('127.0.0.1')
                self.assertFalse(created)
                self.assertIs(obj, None)

                self.assertEqual(models.ISP.objects.count(), 0)
                self.assertEqual(models.IP.objects.count(), 0)

    def test_valid_whois_results(self):
        for valid_ret_val in self.valid_whois_results:
            with patch('tracker.models.whois.whois', return_value=valid_ret_val):
                obj, created = models.ISP.objects.match_or_create(valid_ret_val['ipv4range'][0])
                self.assertTrue(obj is not None)
                self.assertTrue(obj.ip_set.count() > 0)
                self.assertFalse(obj is None)
                obj.delete()

    def test_null_country_and_orgname_are_accepted(self):
        with patch('tracker.models.whois.whois', return_value={'ipv4range': ('127.0.0.0', '127.255.255.255')}):
            obj, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
            self.assertEqual(obj.name, None)
            self.assertEqual(obj.country, None)
            self.assertEqual(obj.ip_set.count(), 1)

    def test_null_country_is_accepted(self):
        with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.255.255.255')}):
            obj, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
            self.assertEqual(obj.name, 'foo')
            self.assertEqual(obj.country, None)
            self.assertEqual(obj.ip_set.count(), 1)

    def test_null_orgname_is_accepted(self):
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'ipv4range': ('127.0.0.0', '127.255.255.255')}):
            obj, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
            self.assertEqual(obj.name, None)
            self.assertEqual(obj.country, 'un')
            self.assertEqual(obj.ip_set.count(), 1)

    def test_same_org_name_range_is_added_to_existing_isp_entry(self):
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.255.255.255')}):
            obj1, created = models.ISP.objects.match_or_create('127.0.0.1')
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'orgname': 'foo', 'ipv4range': ('192.168.1.0', '192.168.1.255')}):
            obj2, created = models.ISP.objects.match_or_create('192.168.1.10')

        self.assertEqual(obj1.pk, obj2.pk)
        self.assertEqual(obj1.name, 'foo')
        self.assertEqual(obj1.ip_set.count(), 2)

    def test_same_org_name_but_different_country_range_is_not_added_to_existing_isp_entry(self):
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.255.255.255')}):
            obj1, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
        with patch('tracker.models.whois.whois', return_value={'country': 'eu', 'orgname': 'foo', 'ipv4range': ('192.168.1.0', '192.168.1.255')}):
            obj2, created = models.ISP.objects.match_or_create('192.168.1.10')
            self.assertTrue(created)

        self.assertNotEqual(obj1.pk, obj2.pk)
        self.assertEqual(obj1.name, 'foo')
        self.assertEqual(obj2.name, 'foo')

    def test_null_orgname_wont_hook_up_to_existing_null_orgname(self):
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'orgname': None, 'ipv4range': ('127.0.0.0', '127.255.255.255')}):
            obj1, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
            self.assertEqual(obj1.name, None)
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'orgname': None, 'ipv4range': ('192.168.1.0', '192.168.1.255')}):
            obj2, created = models.ISP.objects.match_or_create('192.168.1.12')
            self.assertTrue(created)
            self.assertEqual(obj2.name, None)

        self.assertNotEqual(obj1.pk, obj2.pk)
        self.assertEqual(models.IP.objects.count(), 2)

    def test_null_country_will_hook_up_to_existing_null_country(self):
        with patch('tracker.models.whois.whois', return_value={'country': None, 'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.255.255.255')}):
            obj1, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
            self.assertEqual(obj1.name, 'foo')
            self.assertEqual(obj1.country, None)
        with patch('tracker.models.whois.whois', return_value={'country': None, 'orgname': 'foo', 'ipv4range': ('192.168.1.0', '192.168.1.255')}):
            obj2, created = models.ISP.objects.match_or_create('192.168.1.12')
            self.assertFalse(created)
            self.assertEqual(obj2.name, 'foo')
            self.assertEqual(obj2.country, None)
        self.assertEqual(obj1.pk, obj2.pk)
        self.assertEqual(obj1.ip_set.count(), 2)

    def test_matching_range_from_known_ip_range_skips_whois_lookup(self):
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.0.0.255')}):
            obj1, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
            self.assertEqual(obj1.name, 'foo')
            self.assertEqual(obj1.country, 'un')
            self.assertEqual(obj1.ip_set.count(), 1)
        with patch('tracker.models.whois.whois', return_value={'country': 'eu', 'orgname': 'bar', 'ipv4range': ('127.0.0.0', '127.0.0.255')}) as mock:
            obj2, created = models.ISP.objects.match_or_create('127.0.0.2')
            self.assertFalse(mock.called)
            self.assertFalse(created)
            self.assertEqual(obj2.name, 'foo')
            self.assertEqual(obj2.country, 'un')
            self.assertEqual(obj2.ip_set.count(), 1)
        self.assertEqual(obj1.pk, obj2.pk)

    def test_matching_range_from_known_ip_range_skips_whois_lookup_even_null_isp_name(self):
        with patch('tracker.models.whois.whois', return_value={'ipv4range': ('127.0.0.0', '127.0.0.255')}):
            obj1, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(created)
            self.assertIs(obj1.name, None)
            self.assertIs(obj1.country, None)
            self.assertEqual(obj1.ip_set.count(), 1)
        with patch('tracker.models.whois.whois', return_value={'ipv4range': ('127.0.0.0', '127.0.0.255')}) as mock:
            obj2, created = models.ISP.objects.match_or_create('127.0.0.2')
            self.assertFalse(mock.called)
            self.assertFalse(created)
            self.assertIs(obj2.name, None)
            self.assertIs(obj2.country, None)
            self.assertEqual(obj2.ip_set.count(), 1)
        self.assertEqual(obj1.pk, obj2.pk)

    def test_invalid_ip_ranges_from_whois_result_are_ignored(self):
        for invalid_range in self.invalid_ranges:
            with patch('tracker.models.whois.whois', return_value={'ipv4range': invalid_range}):
                obj, created = models.ISP.objects.match_or_create('127.0.0.1')
                self.assertIs(obj, None)
                self.assertFalse(created)

    def test_match_will_prefer_the_smallest_possible_ip_range(self):
        (models.ISP.objects.create(name='foo')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.255.255.255').int()
            )
        )
        (models.ISP.objects.create(name='bar')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.0.255.255').int()
            )
        )
        (models.ISP.objects.create(name='baz')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.0.0.255').int()
            )
        )
        (models.ISP.objects.create(name='ham')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.0.0.1').int()
            )
        )
        (models.ISP.objects.create(name='spam')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.1').int(), 
                range_to=utils.force_ipy('127.0.0.1').int()
            )
        )

        with patch('tracker.models.whois.whois') as mock:
            self.assertEqual(models.ISP.objects.match('127.0.0.1')[0].name, 'spam')
            self.assertEqual(models.ISP.objects.match('127.0.0.2')[0].name, 'baz')
            self.assertEqual(models.ISP.objects.match('127.0.0.0')[0].name, 'ham')
            self.assertEqual(models.ISP.objects.match('127.0.244.15')[0].name, 'bar')
            self.assertEqual(models.ISP.objects.match('127.12.244.15')[0].name, 'foo')
            self.assertEqual(models.ISP.objects.match('127.255.255.255')[0].name, 'foo')
            
            self.assertFalse(mock.called)

    def test_match_or_create_will_fail_to_create_an_ip_range_entry_in_case_the_ip_does_not_fit_in(self):
        with patch('tracker.models.whois.whois', return_value={'ipv4range': ('127.0.0.0', '127.255.255.255')}) as mock:
            obj2, created = models.ISP.objects.match_or_create('192.168.1.1')
            self.assertIs(obj2, None)
            self.assertFalse(created)

    def test_match_or_create_will_not_add_same_ip_range(self):
        (models.ISP.objects.create(name='foo')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.255.255.255').int()
            )
        )
        with patch('tracker.models.ISPManager.match') as match_mock:
            with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.255.255.255')}) as whois_mock:
                match_mock.side_effect = exceptions.ObjectDoesNotExist
                obj, created = models.ISP.objects.match_or_create('127.0.0.1')
                self.assertEqual(obj.name, 'foo')
                self.assertFalse(created)
                self.assertEqual(obj.ip_set.count(), 1)
                self.assertEqual(models.IP.objects.count(), 1)

    def test_too_large_ip_range_will_cause_an_extra_whois_call(self):
        (models.ISP.objects.create(name='foo')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.255.255.255').int()
            )
        )
        with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.255.255.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(mock.called)
            self.assertFalse(created)
            self.assertTrue(obj.name, 'foo')
            # the returned ip range is same
            self.assertEqual(models.IP.objects.count(), 1)

        with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.0.255.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.2')
            self.assertTrue(mock.called)
            self.assertFalse(created)
            self.assertTrue(obj.name, 'foo')
            # the returned ip range is different
            self.assertEqual(models.IP.objects.count(), 2)

    def test_extra_whois_call_will_not_intefere_with_existing_ip_range_entry_assigned_to_different_isp(self):
        # too large ip range, extra whois call is required
        (models.ISP.objects.create(name='foo')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.255.255.255').int()
            )
        )
        (models.ISP.objects.create(name='bar')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.0.0.255').int()
            )
        )
        with patch('tracker.models.whois.whois', return_value={'ipv4range': ('127.0.0.0', '127.0.0.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertFalse(mock.called)
            self.assertFalse(created)
            self.assertTrue(obj.name, 'bar')

        # although an extra whois call was performed, the resolved ip range had already existed
        # and it had been assigned to a different isp
        with patch('tracker.models.ISPManager.match') as match_mock:
            with patch('tracker.models.whois.whois', return_value={'orgname': 'ham', 'ipv4range': ('127.0.0.0', '127.0.0.255')}) as whois_mock:
                match_mock.side_effect = exceptions.ObjectDoesNotExist
                obj, created = models.ISP.objects.match_or_create('127.0.0.2')
                self.assertEqual(obj.name, 'bar')
                self.assertTrue(whois_mock.called)
                self.assertFalse(created)

    def test_extra_whois_call_will_prevent_further_whois_lookups_if_the_range_length_is_okay(self):
        # too large ip range, extra whois call is required
        (models.ISP.objects.create(name='foo')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.255.255.255').int()
            )
        )
        with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.0.0.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(mock.called)
            self.assertFalse(created)

        with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.0.0.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.2')
            self.assertFalse(mock.called)
            self.assertFalse(created)

        with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.0.0.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.128')
            self.assertFalse(mock.called)
            self.assertFalse(created)

        self.assertEqual(models.IP.objects.count(), 2)

    def test_extra_whois_call_returns_same_ip_range(self):
        (models.ISP.objects.create(name='foo')
            .ip_set.create(
                range_from=utils.force_ipy('127.0.0.0').int(), 
                range_to=utils.force_ipy('127.255.255.255').int()
            )
        )
        # ip range is too large
        with patch('tracker.models.whois.whois', return_value={'orgname': 'foo', 'ipv4range': ('127.0.0.0', '127.255.255.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.1')
            self.assertTrue(mock.called)
            self.assertFalse(created)
        # same ip range, but different orgname
        with patch('tracker.models.whois.whois', return_value={'orgname': 'bar', 'ipv4range': ('127.0.0.0', '127.255.255.255')}) as mock:
            obj, created = models.ISP.objects.match_or_create('127.0.0.2')
            self.assertTrue(mock.called)
            self.assertFalse(created)


class ProfileTestCase(TestCase):

    def setUp(self):
        super(ProfileTestCase, self).setUp()
        self.test_game = models.Game.objects.create()

    def test_match_will_match_against_known_pair_of_name_ip(self):
        profile1 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile1.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        obj = models.Profile.objects.match(name='Serge', player__ip='127.0.0.1')
        self.assertEqual(profile1.pk, obj.pk)

    def test_match_smart_with_no_args_wont_match_anything(self):
        profile1 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile1.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        profile2 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile2.alias_set.create(name='foo', isp=models.ISP.objects.create()), ip='127.0.0.1')

        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_smart()

    def test_match_smart_will_prefer_name_range_to_name_isp(self):
        isp1 = models.ISP.objects.create()
        isp2 = models.ISP.objects.create()

        profile1 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile1.alias_set.create(name='Serge', isp=isp1), ip='127.0.0.1')

        profile2 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile2.alias_set.create(name='Serge', isp=isp2), ip='192.168.1.10')

        self.assertEqual(models.Profile.objects.match_smart(name='Serge', ip='127.0.0.1', isp=isp2).pk, profile1.pk)
        self.assertEqual(models.Profile.objects.match_smart(name='Serge', ip='192.168.1.10', isp=isp1).pk, profile2.pk)

    def test_match_smart_null_isp_will_not_match_against_existing_null_isp(self):
        profile1 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile1.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        self.assertRaises(exceptions.ObjectDoesNotExist, models.Profile.objects.match_smart, name='Serge', isp=None)
        self.assertRaises(exceptions.ObjectDoesNotExist, models.Profile.objects.match_smart, name='Serge', ip='127.0.0.2')

    def test_match_smart_non_empty_isp_will_not_match_against_existing_null_isp(self):
        profile1 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile1.alias_set.create(name='Serge', isp=models.ISP.objects.create()), ip='127.0.0.1')

        self.assertRaises(exceptions.ObjectDoesNotExist, models.Profile.objects.match_smart, name='Serge', isp=None)
        self.assertRaises(exceptions.ObjectDoesNotExist, models.Profile.objects.match_smart, name='Serge', ip='127.0.0.2')

    def test_match_smart_will_not_match_other_profiles_with_null_isp(self):
        profile1 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile1.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        profile2 = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile2.alias_set.create(name='Serge', isp=None), ip='127.0.0.2')

        obj, created = models.Profile.objects.match_smart_or_create(name='Serge', ip='192.168.1.10', isp=None)
        self.assertTrue(created)
        self.assertNotEqual(profile1.pk, obj.pk)

    def test_match_smart_will_not_perform_whois_lookup_if_isp_is_present_even_none(self):
        with patch('tracker.models.whois.whois', return_value={'ipv4range': ('127.0.0.0', '127.255.255.255')}) as mock:
            profile, created = models.Profile.objects.match_smart_or_create(name='Serge', ip='127.0.0.1', isp=None)
            self.assertFalse(mock.called)

    def test_match_smart_will_perform_whois_lookup_no_isp_provided(self):
        with patch('tracker.models.whois.whois', return_value={'orgname': 'localhost', 'ipv4range': ('127.0.0.0', '127.255.255.255')}) as mock:
            profile, created = models.Profile.objects.match_smart_or_create(name='Serge', ip='127.0.0.1')
            self.assertTrue(mock.called)
            self.assertTrue(created)
            self.assertEqual(models.ISP.objects.get().name, 'localhost')
            self.assertEqual(
                models.IP.objects.values('range_from', 'range_to').get(), 
                {'range_from': 2130706432, 'range_to': 2147483647}
            )

    def test_match_smart_will_not_match_against_popular_names(self):
        isp = models.ISP.objects.create()
        profile = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Player', isp=isp), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='afk5min', isp=isp), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='newname', isp=isp), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='TODOsetname2', isp=isp), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=isp), ip='127.0.0.1')
        
        models.Profile.objects.match_smart(name='Serge', ip='127.0.0.3', isp=isp)

        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_smart(name='Player', ip='127.0.0.3', isp=isp)
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_smart(name='TODOsetname2', ip='127.0.0.3', isp=isp)
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_smart(name='newname', ip='127.0.0.3', isp=isp)

    def test_popular_names(self):
        popular_names = (
            'Player', 'player', 'Player2', 'player3', 
            'newname', 'swat', 'lol', 'TODOsetname2231',
            'afk', 'afk5min', 'afk_dont_kick', 'killer',
            'spieler', 'gracz', 'testing', 'test', 'testing_mod',
        )
        for name in popular_names:
            self.assertTrue(models.Profile.is_name_popular(name), '%s is not popular' % name)

    def test_popular_qualification(self):
        real_now = timezone.now

        with patch.object(timezone, 'now') as mock:
            mock.return_value = real_now() - datetime.timedelta(seconds=models.Profile.TIME_POPULAR + 100)
            game = models.Game.objects.create()

        profile = models.Profile.objects.create()

        game.player_set.create(alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1')
        game.player_set.create(alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        self.assertEqual(profile.fetch_popular_name(), None)

        game = models.Game.objects.create()
        game.player_set.create(alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            self.assertEqual(profile.fetch_popular_name(), 'Serge')

    def test_popular_name(self):
        profile = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='afk', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.4')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.3')

        another_profile = models.Profile.objects.create()
        models.Player.objects.create(game=self.test_game, alias=another_profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=another_profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.7')
        models.Player.objects.create(game=self.test_game, alias=another_profile.alias_set.create(name='Player', isp=None), ip='127.0.0.2')
        models.Player.objects.create(game=self.test_game, alias=another_profile.alias_set.create(name='Player', isp=None), ip='127.0.0.3')

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            self.assertEqual(profile.fetch_popular_name(), 'Serge')
            self.assertEqual(another_profile.fetch_popular_name(), 'Player')

    def test_popular_country(self):
        profile = models.Profile.objects.create()
        isp1 = models.ISP.objects.create(country='un')
        isp2 = models.ISP.objects.create(country='eu')
        isp3 = models.ISP.objects.create(country='uk')

        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=isp1), ip='127.0.0.1')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Player', isp=isp1), ip='127.0.0.121')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=isp2), ip='127.0.0.143')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=isp2), ip='127.0.0.11')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=isp2), ip='127.0.0.12')
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Player', isp=isp3), ip='127.0.0.3')

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            self.assertEqual(profile.fetch_popular_country(), 'eu')

    def test_popular_team(self):
        profile = models.Profile.objects.create()

        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='afk', isp=None), ip='127.0.0.1', team=0)
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.1', team=0)
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1', team=0)
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.1', team=1)
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Serge', isp=None), ip='127.0.0.4', team=1)
        models.Player.objects.create(game=self.test_game, alias=profile.alias_set.create(name='Player', isp=None), ip='127.0.0.3', team=0)

        with patch.object(models.Profile, 'MIN_PLAYERS', new=PropertyMock(return_value=0)):
            self.assertEqual(profile.fetch_popular_team(), 0)


class ProfileMatchTestCase(TestCase):

    def setUp(self):
        super(ProfileMatchTestCase, self).setUp()
        with patch('tracker.models.whois.whois', return_value={'country': 'un', 'orgname': 'foo', 'ipv4range': ('127.255.255.0', '127.255.255.255')}):
            self.server1 = models.Server.objects.create(ip='127.0.0.1', port=10480)
            self.server2 = models.Server.objects.create(ip='127.0.0.1', port=10580)
        
        self.isp1 = models.ISP.objects.create(name='foo', country='jp')
        self.isp2 = models.ISP.objects.create(name='bar', country='uk')
        self.isp3 = models.ISP.objects.create(name='ham', country='es')

        self.profile1 = models.Profile.objects.create()
        self.profile2 = models.Profile.objects.create()
        self.profile3 = models.Profile.objects.create()
        self.profile4 = models.Profile.objects.create()
        self.profile5 = models.Profile.objects.create()

        self.alias1 = models.Alias.objects.create(profile=self.profile1, name='Serge', isp=self.isp1)
        self.alias2 = models.Alias.objects.create(profile=self.profile2, name='spam', isp=self.isp1)
        self.alias3 = models.Alias.objects.create(profile=self.profile3, name='django', isp=self.isp2)
        self.alias4 = models.Alias.objects.create(profile=self.profile4, name='python', isp=self.isp3)
        self.alias5 = models.Alias.objects.create(profile=self.profile5, name='bar', isp=self.isp3)

        now = timezone.now()

        with patch.object(timezone, 'now') as mock:
            mock.return_value = now - datetime.timedelta(days=365)
            self.game1 = models.Game.objects.create(server=self.server1)

        # game played year ago
        self.game1.player_set.create(alias=self.alias1, ip='11.11.11.11')
        self.game1.player_set.create(alias=self.alias2, ip='22.22.22.22')
        self.game1.player_set.create(alias=self.alias3, ip='44.44.44.44')
        self.game1.player_set.create(alias=self.alias4, ip='55.55.55.55')
        self.game1.player_set.create(alias=self.alias5, ip='66.66.66.77')

        # game that has just been finished
        self.game2 = models.Game.objects.create(
            server=self.server2, date_finished=timezone.now()
        )

        player1 = self.game2.player_set.create(alias=self.profile3.alias_set.create(name='baz', isp=self.isp1), ip='4.5.6.7')
        player2 = self.game2.player_set.create(alias=self.profile3.alias_set.create(name='bar', isp=self.isp2), ip='1.2.3.4')

        self.game2.player_set.add(player1)
        self.game2.player_set.add(player2)

    def test_match_recent(self):
        obj1 = models.Profile.objects.match_recent(name='baz', isp=self.isp1)
        obj1 = models.Profile.objects.match_recent(name='bar', isp=self.isp2)
        obj2 = models.Profile.objects.match_recent(player__ip='1.2.3.4')
        self.assertEqual(obj1.pk, self.profile3.pk)
        self.assertEqual(obj1.pk, self.profile3.pk)
        self.assertEqual(obj2.pk, self.profile3.pk)

        # old game
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_recent(player__ip='11.11.11.11')
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_recent(name='Serge', player__ip='11.11.11.11')
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_recent(name='Serge', isp=self.isp1)

        # did not participate
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_recent(name='eggs', player__ip='5.6.7.8')
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_recent(name='eggs', isp=self.isp3)

    def test_match_smart_or_create(self):

        obj, created = models.Profile.objects.match_smart_or_create(ip='20.20.20.20', isp=None)
        self.assertTrue(created)

        # no args
        obj, created = models.Profile.objects.match_smart_or_create()
        self.assertTrue(created)

        # different case
        obj, created = models.Profile.objects.match_smart_or_create(name='serge', ip='11.11.11.11', isp=None)
        self.assertFalse(created)

        # old game
        obj, created = models.Profile.objects.match_smart_or_create(ip='4.4.4.4', isp=None)
        self.assertTrue(created)

        # different case but recently played
        obj, created = models.Profile.objects.match_smart_or_create(name='BAZ', ip='4.5.6.7', isp=None)
        self.assertFalse(created)

        # duplicate name but only the latter quilifies for recently played
        obj, created = models.Profile.objects.match_smart_or_create(name='BAR', ip='1.2.3.4', isp=None)
        self.assertFalse(created)
        obj, created = models.Profile.objects.match_smart_or_create(name='bar', ip='1.2.3.4', isp=None)
        self.assertFalse(created)

        # recent ip
        obj, created = models.Profile.objects.match_smart_or_create(ip='1.2.3.4', isp=None)
        self.assertFalse(created)

        # not recent ip
        obj, created = models.Profile.objects.match_smart_or_create(ip='44.44.44.44', isp=None)
        self.assertTrue(created)

        # the ip has not been used in games
        obj, created = models.Profile.objects.match_smart_or_create(ip='5.6.7.8', isp=None)
        self.assertTrue(created)

    def test_match_smart_name_country(self):
        isp1 = models.ISP.objects.create(name='spam', country='jp')
        isp2 = models.ISP.objects.create(name='eggs', country='pt')

        self.assertEqual(models.Profile.objects.match_smart(name='baz', ip='192.168.1.25', isp=isp1).pk, self.profile3.pk)

        # game is recent but country doesnt match
        with self.assertRaises(exceptions.ObjectDoesNotExist):
            models.Profile.objects.match_smart(name='baz', ip='192.168.1.25', isp=isp2)


class ProfileMatchTestCase2(TestCase):

    def test_player_gets_same_profile_after_name_change(self):
        isp = models.ISP.objects.create()
        profile = models.Profile.objects.create()

        alias1 = profile.alias_set.create(profile=profile, name='Player', isp=isp)
        models.Game.objects.create().player_set.create(
            alias=alias1, ip='127.0.0.1'
        )

        alias2 = models.Alias.objects.match_or_create(name='Serge', ip='127.0.0.1', isp=isp)[0]
        models.Game.objects.create().player_set.create(
            alias=alias2, ip='127.0.0.1'
        )
        
        self.assertEqual(alias1.profile.pk, alias2.profile.pk)


    def test_player_does_not_receive_same_profile_after_long_period(self):
        isp = models.ISP.objects.create()
        profile = models.Profile.objects.create()
        now = timezone.now

        alias1 = profile.alias_set.create(profile=profile, name='Player', isp=isp)
        with patch.object(timezone, 'now') as mock:
            mock.return_value = now() - datetime.timedelta(seconds=models.Profile.TIME_RECENT+1)
            models.Game.objects.create().player_set.create(
                alias=alias1, ip='127.0.0.1'
            )

        alias2 = models.Alias.objects.match_or_create(name='Serge', ip='127.0.0.1', isp=isp)[0]
        models.Game.objects.create().player_set.create(
            alias=alias2, ip='127.0.0.1'
        )
        
        self.assertNotEqual(alias1.profile.pk, alias2.profile.pk)
