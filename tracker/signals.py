# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import logging
from datetime import datetime

import six
from django.dispatch import receiver, Signal
from django.db.models.signals import post_save
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_text

from . import models, utils
from .definitions import STATS, MODE_VIP, MODE_BS, MODE_RD, MODE_SG, MODES_COOP

logger = logging.getLogger(__name__)

stream_data_received = Signal(providing_args=['data', 'server'])
stream_data_saved = Signal(providing_args=['data', 'server', 'game', 'players'])


#@receiver(stream_data_saved)
@transaction.atomic
def cache_profile_overall_score(sender, data, server, game, **kwargs):
    """
    Retrieve and cache overall score of all players participated in the round.
    """
    options = (
        models.Profile.SET_STATS_COMMON | 
        models.Profile.SET_STATS_KILLS | 
        models.Profile.SET_STATS_WEAPONS
    )
    gametype = int(game.gametype)
    # VIP Escort
    if gametype == MODE_VIP:
        options |= models.Profile.SET_STATS_VIP
    # Rapid Deployment
    elif gametype == MODE_RD:
        options |= models.Profile.SET_STATS_RD
    # Smash and Grab
    elif gametype == MODE_SG:
        options |= models.Profile.SET_STATS_SG
    # COOP
    elif gametype in MODES_COOP:
        # rewrite options (dont need any of the standard options)
        options = models.Profile.SET_STATS_COOP
    # aggregate stats relative to the game's date
    year = game.date_finished.year
    period = models.Rank.get_period_for_year(year)

    for player in game.player_set.select_related('profile'):
            for category, points in six.iteritems(player.profile.aggregate_mode_stats(options, *period)):
                # create or update the calculated points along with the assotiated profile
                models.Rank.objects.store(category, year, player.profile, points)


#@receiver(stream_data_saved)
@transaction.atomic
def update_profile_details(sender, data, server, game, players, **kwargs):
    """
    Retrieve profile instances of the players particiapted in the game of
    and cache their popular name, team, country and loadout.
    """
    for player in players:
        # update the profile's popular items
        player.profile.update_popular(save=True)


#@receiver(stream_data_saved)
@transaction.atomic
def update_profile_last_seen(sender, data, server, game, players, **kwargs):
    """
    Bulk update the profile entries last seen date of the particiapted players.
    """
    (models.Profile.objects
        .filter(pk__in=list(map(lambda player: player.profile.pk, players)))
        .update(date_played=game.date_finished)
    )


@receiver(stream_data_received)
@transaction.atomic
def save_game(sender, data, server, **kwargs):
    """
    Save a Game entry upon receiving data from one of the streaming servers
    Also attempt to save assotiated Objective, Procedures and Player objects, if supplied.
    """
    players = []
    # insert a new game entry
    game = server.game_set.create(
        tag=data['tag'].value, 
        gametype=int(data['gametype'].raw), 
        mapname=int(data['mapname'].raw), 
        outcome=int(data['outcome'].raw),
        time=data['time'].value, 
        player_num=data['player_num'].value,
        score_swat=data['score_swat'].value,
        score_sus=data['score_sus'].value,
        vict_swat=data['vict_swat'].value,
        vict_sus=data['vict_sus'].value,
        rd_bombs_defused=data['bombs_defused'].value,
        rd_bombs_total=data['bombs_total'].value,
        # calculate coop score 100 max
        coop_score=min(100, (utils.calc_coop_score(data['coop_procedures']) if data.get('coop_procedures', None) else 0)),
    )
    # insert objectives in bulk
    if data.get('coop_objectives', None) is not None:
        models.Objective.objects.bulk_create([
            models.Objective(
                game=game, 
                # both items are mappings, insert the raw values instead
                name=int(obj['name'].raw), 
                status=int(obj['status'].raw),
            )
            for obj in data['coop_objectives']
        ])
    # insert procedures in bulk
    if data.get('coop_procedures', None) is not None:
        models.Procedure.objects.bulk_create([
            models.Procedure(
                game=game, 
                # name is a mapping, insert its raw value
                name=int(pro['name'].raw), 
                status=pro['status'].value,
                score=pro['score'].value,
            )
            for pro in data['coop_procedures']
        ])
    # insert players
    if data.get('players', None) is not None:
        # sorry for obvious comments
        # i need something other than empty lines to delimit blocks of code :-)
        for raw_player in data['players']:
            # attempt to parse loadout
            loadout = {}
            for key in models.Loadout.FIELDS:
                try:
                    value = int(raw_player['loadout'][key].raw)
                except (KeyError, ValueError, TypeError):
                    # set zeroes (None) for absent items
                    value = '0'
                finally:
                    loadout[key] = value
            # insert a Player entry
            player = game.player_set.create(
                # team is a mapping, insert a raw (0 or 1)
                team=int(raw_player['team'].raw),
                vip=raw_player['vip'].value,
                admin=raw_player['admin'].value,
                dropped=raw_player['dropped'].value,
                # coop status is also a mapping
                coop_status=int(raw_player['coop_status'].raw),
                loadout=models.Loadout.objects.get_or_create(**loadout)[0],
                # retrive profile, alias and isp
                **models.Player.profile_alias(
                    # prevent empty and coloured names
                    utils.force_name(raw_player['name'].value, raw_player['ip'].value),
                    raw_player['ip'].value,
                )
            )
            # insert Player score in bulk (unless its a zero)
            models.Score.objects.bulk_create([
                models.Score(
                    player=player, 
                    category=category,
                    points=raw_player[key].value
                )
                for category, key in STATS if (key in raw_player and raw_player[key].value != 0)
            ])
            # insert Player weapons in bulk .. unless its a COOP game
            if raw_player['weapons'] is not None:
                models.Weapon.objects.bulk_create([
                    models.Weapon(
                        player=player,
                        name=int(weapon['name'].raw),
                        time=weapon['time'].value,
                        shots=weapon['shots'].value,
                        hits=weapon['hits'].value,
                        teamhits=weapon['teamhits'].value,
                        kills=weapon['kills'].value,
                        teamkills=weapon['teamkills'].value,
                        # convert cm to meters (true division is on)
                        distance=weapon['distance'].value / 100,
                    )
                    for weapon in raw_player['weapons']
                ])
            players.append(player)
    # emit a signal
    stream_data_saved.send(sender=None, data=data, server=server, game=game, players=players)


@receiver(stream_data_received)
@transaction.atomic
def update_server_status(sender, data, server, **kwargs):
    """
    Update server's status upon receiving stream data from that server.
    Attempt to update status of the players participated in the game, if supplied.
    """
    # append items with raw values
    defaults = {
        'gamename': data['gamename'].raw,
        'gamever': data['gamever'].value,
        'hostname': data['hostname'].value,
        'passworded': data['passworded'].value,
        'gametype': data['gametype'].raw,
        'mapname': data['mapname'].raw,
        'player_num': data['player_num'].value,
        'player_max': data['player_max'].value,
        'round_num': data['round_num'].value,
        'round_max': data['round_max'].value,
        'score_swat': data['score_swat'].value,
        'score_sus': data['score_sus'].value,
        'vict_swat': data['vict_swat'].value,
        'vict_sus': data['vict_sus'].value,
        'rd_bombs_defused': data['bombs_defused'].value,
        'rd_bombs_total': data['bombs_total'].value,
    }
    obj, created = models.ServerStatus.objects.get_or_create(server=server, defaults=defaults)
    # update the pre-existed entry
    if not created:
        for attr in defaults:
            setattr(obj, attr, defaults[attr])
        obj.save()