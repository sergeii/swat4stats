# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import re
import logging
import datetime
import random
import string
from optparse import make_option

from mock import patch
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Min
from django.db import transaction, reset_queries
from django.utils import timezone, encoding
from whois import int2ip

import stats7
import tracker
from tracker.definitions import shortcuts, stream_pattern_node, MODE_VIP

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--insert',
            action='store_true',
            dest='insert',
            default=False,
        ),
    )

    def handle(self, *args, **options):

        if options['insert']:
            self.FIX_MAP = stats7.models.Round.objects.aggregate(min=Min('map'))['min'] * -1
            self.SERVERS = {
                'myt1': tracker.models.Server.objects.get_or_create(ip='81.19.209.212', port=10480, defaults={'key': 'foo'})[0],
                'myt2': tracker.models.Server.objects.get_or_create(ip='81.19.209.212', port=10580, defaults={'key': 'bar'})[0],
            }
            if self.FIX_MAP:
                logger.debug('will mapfix')

        rounds_good = 0
        rounds_bad = 0
        rounds_total = 0

        qs = stats7.models.Round.objects.all()

        if args:
            qs = qs[:int(args[0])]

        for round in qs:
            rounds_total += 1

            score_calculated = 0
            score_expected = round.swatscore + round.suspectsscore
            outcome_expected = get_outcome(round.reason, round.won)
            outcome_expected_readable = shortcuts.map(
                stream_pattern_node, 'outcome', encoding.force_text(outcome_expected)
            )
            outcome_calculated_readable = None

            players = round.roundplayer_set.select_related('player').all()
            numplayers_calculated = players.filter(dropped=False, finished=True).count()

            finished = []
            unfinished = {}
            warning = None

            try:
                assert abs(round.numplayers - numplayers_calculated) <= 2, \
                    'round.numplayers %s!=%s' % (round.numplayers, numplayers_calculated)
                
                for player in players:
                    name = player.player.name.strip()
                    # name must not be empty
                    try:
                        assert name, 'name of %s is empty' % player.pk
                    except AssertionError as e:
                        logger.warning(str(e))
                    assert (player.is_swat + player.is_sus + player.is_vip == 1)

                    if player.vipescaped > 0:
                        assert player.is_vip, '%s is not the VIP' % name
                        assert round.won == 1, \
                            'round.won is %s, want %s' % (round.won, 1)
                        assert round.reason == 3, \
                            'reason is %s, want %s (vip escaped)' % (round.reason, 3)
                        assert outcome_expected_readable == 'swat_vip_escape', \
                            'outcome_expected_readable is %s, want %s' % (outcome_expected_readable, 'swat_vip_escape')
                        outcome_calculated_readable = 'swat_vip_escape'

                    if player.validvipkills > 0:
                        assert player.is_sus, '%s is not a suspect' % name
                        assert round.won == 2, \
                            'round.won is %s, want %s (sus goodkilled vip)' % (round.won, 2)
                        assert round.reason == 2, \
                            'reason is %s, want %s' % (round.reason, 2)
                        assert outcome_expected_readable == 'sus_vip_good_kill', \
                            'outcome_expected_readable is %s, want %s' % (outcome_expected_readable, 'sus_vip_good_kill')
                        outcome_calculated_readable = 'sus_vip_good_kill'

                    if player.invalidvipkills > 0:
                        assert (not player.is_vip), \
                            '%s (the VIP) has %s invalid vip kills' % (name, player.invalidvipkills)
                        assert round.reason == 1, \
                            'reason is %s, want %s' % (round.reason, 1)
                        
                        if player.is_swat:
                            assert round.won == 2, \
                                'round.won is %s, want %s (swat badkilled vip)' % (round.won, 2)
                            assert outcome_expected_readable == 'sus_vip_bad_kill', \
                                'outcome_expected_readable is %s, want %s' % (outcome_expected_readable, 'sus_vip_bad_kill')
                            outcome_calculated_readable = 'sus_vip_bad_kill'

                        if player.is_sus:
                            assert round.won == 1, \
                                'round.won is %s, want %s (sus badkilled vip)' % (round.won, 1)
                            assert outcome_expected_readable == 'swat_vip_bad_kill', \
                                'outcome_expected_readable is %s, want %s' % (outcome_expected_readable, 'swat_vip_bad_kill')
                            outcome_calculated_readable = 'swat_vip_bad_kill'

                    if player.is_vip and player.dropped and not round.won:
                        assert player.finished, \
                            '%s was the vip and dropped but did not finish' % name
                        assert round.reason == 5, \
                            'reason is %s, want %s (vip dropped)' % (round.reason, 5)
                        assert outcome_expected_readable == 'tie', \
                            'outcome_expected_readable is %s, want %s' % (outcome_expected_readable, 'tie')
                        outcome_calculated_readable = 'tie'

                    if player.is_vip and player.deaths and not round.won:
                        assert player.finished, \
                            '%s was the vip and dropped but did not finish' % name
                        assert round.reason == 6, \
                            '%s is the reason, want %s (vip suicided)' % (round.reason, 6)
                        assert outcome_expected_readable == 'tie', \
                            'outcome_expected_readable is %s, want %s' % (outcome_expected_readable, 'tie')
                        outcome_calculated_readable = 'tie'

                    if player.finished:
                        finished.append(player)
                    else:
                        unfinished.setdefault(player.player_id, [])
                        unfinished[player.player_id].append(player)

                for player in finished:
                    if player.player_id in unfinished:
                        for u in unfinished[player.player_id]:
                            player.time += u.time
                            player.kills += u.kills
                            player.tkills += u.tkills
                            player.deaths += u.deaths
                            player.arrests += u.arrests
                            player.arrested += u.arrested
                            player.arrestedvip += u.arrestedvip
                            player.unarrestedvip += u.unarrestedvip
                            player.vipescaped += u.vipescaped
                    player_score_calculated = get_score(player)

                    assert player.score == player_score_calculated, \
                        'player.score %s != %s' % (player.score, player_score_calculated)
                    score_calculated += player_score_calculated

                if outcome_calculated_readable is None:
                    assert round.won == 0, \
                        'round.won should be 0, not %s' % round.won
                    outcome_calculated_readable = 'tie'

                assert outcome_expected_readable == outcome_calculated_readable, \
                    'outcome_expected_readable is %s, want %s' % (outcome_expected_readable, outcome_calculated_readable)

                # 3 unnoticed tks
                assert abs(score_calculated - score_expected) <= 9, \
                    'score_calculated %s != %s' % (score_calculated, score_expected)

            except AssertionError as e:
                rounds_bad += 1
                logger.critical('failure in #{} - {}'.format(round.pk, str(e)))
            else:
                rounds_good += 1
                if options['insert']:
                    self.convert_round(round, finished, outcome_expected)
                    reset_queries()
                #logger.debug('OK #{}: {}'.format(round.pk, outcome_expected_readable))
            if not rounds_total % 1000:
                self.stdout.write('%s rounds total. %s good. %s bad' % (rounds_total, rounds_good, rounds_bad))
        
        self.stdout.write('%s rounds total. %s good. %s bad' % (rounds_total, rounds_good, rounds_bad))

    def convert_round(self, round, finished_players, outcome):
        score_keys = (
            (tracker.const.STATS_SCORE, 'score'),
            (tracker.const.STATS_TIME, 'time'),
            (tracker.const.STATS_KILLS, 'kills'),
            (tracker.const.STATS_TEAMKILLS, 'tkills'),
            (tracker.const.STATS_DEATHS, 'deaths'),
            (tracker.const.STATS_ARRESTS, 'arrests'),
            (tracker.const.STATS_ARRESTED, 'arrested'),
            (tracker.const.STATS_VIP_CAPTURES, 'arrestedvip'),
            (tracker.const.STATS_VIP_RESCUES, 'unarrestedvip'),
            (tracker.const.STATS_VIP_ESCAPES, 'vipescaped'),
            (tracker.const.STATS_VIP_KILLS_VALID, 'validvipkills'),
            (tracker.const.STATS_VIP_KILLS_INVALID, 'invalidvipkills'),
        )
        with transaction.atomic():
            with patch.object(timezone, 'now') as mock:
                round_date = datetime.datetime.fromtimestamp(round.roundend).replace(tzinfo=timezone.utc)
                mock.return_value = round_date
                
                for player in finished_players:
                    assert get_score(player) == player.score, 'score wtf?'

                game = tracker.models.Game.objects.create(
                    server=self.SERVERS[round.server],
                    mapname=round.map + self.FIX_MAP,
                    vict_swat=round.swatwon,
                    vict_sus=round.suspectswon,
                    score_swat=round.swatscore,
                    score_sus=round.suspectsscore,
                    time=round.roundtime,
                    player_num=round.numplayers,
                    gametype=MODE_VIP,
                    outcome=outcome
                )
                for player in finished_players:
                    p = game.player_set.create(
                        dropped=bool(player.dropped),
                        loadout=tracker.models.Loadout.objects.get_or_create(**get_loadout(player))[0],
                        team=0 if (player.is_vip or player.is_swat) else 1,
                        vip=bool(player.is_vip),
                        **tracker.models.Player.profile_name_ip_isp(
                            name=tracker.utils.force_name(player.player.name, player.ip), 
                            ip=int2ip(player.ip)
                        )
                    )
                    if player.player.name != p.name:
                        logger.warning('the name {} of {} has been replaced with {}'
                            .format(player.player.name, int2ip(player.ip), p.name)
                        )
                    tracker.models.Score.objects.bulk_create([
                        tracker.models.Score(
                            player=p, 
                            category=category,
                            points=getattr(player, key)
                        )
                        for category, key in score_keys if getattr(player, key) != 0
                    ])
                if not hasattr(self, 'count'):
                    self.count = 0
                self.count += 1
                self.stdout.write('# %d' % self.count)
                #www.signals.stream_data_saved.send(sender=None, game=game, server=self.SERVERS[round.server])


def get_loadout(player):
    weapons = [int(x) for x in re.findall(r'\d{2}', player.weapons)]
    equipment = [int(player.equipment[x]) for x in range(9)]

    if equipment[7]:
        breacher = 3
    elif equipment[8]:
        breacher = 30
    else:
        breacher = 0

    loadout = {
        'primary': weapons[0],
        'primary_ammo': weapons[1],
        'secondary': weapons[2],
        'secondary_ammo': weapons[3],
        'head': weapons[4],
        'body': weapons[5],
        'breacher': breacher,
        'equip_one': 0,
        'equip_two': 0,
        'equip_three': 0,
        'equip_four': 0,
        'equip_five': 0,
    }

    slot_eq = equipment[:7]

    while (sum(slot_eq)):
        for i, weapon in enumerate(slot_eq):
            encoded = {
                0: 18,  # VIPGrenade
                1: 23,  # FlashbangGrenade
                2: 24,  # CSGasGrenade
                3: 25,  # stringGrenade
                4: 26,  # PepperSpray
                5: 27,  # Optiwand
                6: 29,  # Wedge
            }[i]
            if not slot_eq[i]:
                continue
            for slot in ('equip_one', 'equip_two', 'equip_three', 'equip_four', 'equip_five'):
                if loadout[slot] > 0:
                    continue
                else:
                    loadout[slot] = encoded
                    slot_eq[i] -= 1
                    break
    return loadout

def get_score(player):
    return (
        player.kills 
        - player.tkills*3 
        + player.arrests*5 
        + player.validvipkills*10 
        + player.vipescaped*10 
        - player.invalidvipkills*51 
        + player.arrestedvip*10 
        + player.unarrestedvip*10
    )


def get_outcome(reason, won):
    """
    $reason_info = array(
        'unknown'           =>  0,
        'invalidvipkill'    =>  1,
        'validvipkill'      =>  2,
        'vipescaped'        =>  3,
        'draw_time'         =>  4,
        'vipdropped'        =>  5,
        'vipsuicide'        =>  6,
        //'admin_stop'      =>  7,
    );
    """
    if reason == 0:
        return 0
    if won == 0 or reason in (4, 5, 6):
        return shortcuts.unmap(stream_pattern_node, 'outcome', 'tie')
    if reason == 3:
        return shortcuts.unmap(stream_pattern_node, 'outcome', 'swat_vip_escape')
    if reason == 1 and won == 1:
        return shortcuts.unmap(stream_pattern_node, 'outcome', 'swat_vip_bad_kill')
    if reason == 1 and won == 2:
        return shortcuts.unmap(stream_pattern_node, 'outcome', 'sus_vip_bad_kill')
    if reason == 2:
        return shortcuts.unmap(stream_pattern_node, 'outcome', 'sus_vip_good_kill')