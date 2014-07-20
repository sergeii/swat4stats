# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import logging
from datetime import datetime

import six
from django.dispatch import receiver, Signal
from django.db.models import F
from django.db.models.signals import pre_save, post_save
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.utils.encoding import force_text

from . import models, utils
from .definitions import STATS, MODE_VIP, MODE_BS, MODE_RD, MODE_SG, MODES_COOP

logger = logging.getLogger(__name__)

query_status_received = Signal(providing_args=['server', 'status'])
query_status_failed = Signal(providing_args=['server'])
stream_data_received = Signal(providing_args=['data', 'server', 'raw'])
stream_data_saved = Signal(providing_args=['data', 'server', 'game', 'players'])
live_servers_detected = Signal(providing_args=['servers'])
dead_servers_detected = Signal(providing_args=['servers'])


@receiver(pre_save, sender=models.Server)
def validate_server_instance(sender, instance, **kwargs):
    """Validate a Server instance upon saving."""
    instance.clean()


@receiver(live_servers_detected)
def update_server_hostname(sender, servers, **kwargs):
    """Attempt to update server hostname."""
    for server in servers:
        try:
            status = server.status
            assert status
        except:
            # no status available
            # try another server
            continue
        try:
            # only update server hostname in case it's different from the status value
            if server.hostname != status.hostname:
                server.hostname = status.hostname
                server.save(update_fields=['hostname'])
        except:
            # ignore db errors
            pass


@receiver(live_servers_detected)
def enable_server_data_streaming(sender, servers, **kwargs):
    """Enable data streaming for live servers."""
    (models.Server.objects
        .filter(pk__in=list(map(lambda server: server.pk, servers)))
        .update(streamed=True)
    )


@receiver(dead_servers_detected)
def unlist_dead_servers(sender, servers, **kwargs):
    """Remove dead servers from the query list."""
    (models.Server.objects
        .filter(pk__in=list(map(lambda server: server.pk, servers)))
        .update(listed=False)
    )
    if servers:
        logger.debug('Unlisted %s servers' % len(servers))


@receiver(stream_data_saved)
def relist_streaming_server(sender, data, server, game, players, **kwargs):
    """Enable status querying for a streaming server."""
    if not server.listed:
        server.listed = True
        server.save(update_fields=['listed'])
        logger.debug('Relisted a streaming server (%s)' % server)


@receiver(stream_data_saved)
@transaction.atomic
def update_profile_game_reference(sender, data, server, game, players, **kwargs):
    """Bulk update the profile entries of the pariciapted players with the reference to the saved game."""
    # get the profile pks 
    pks = list(map(lambda player: player.alias.profile_id, players))  # avoid profile.pk
    # set first played game
    models.Profile.objects.filter(pk__in=pks, game_first__isnull=True).update(game_first=game)
    # set last played game
    models.Profile.objects.filter(pk__in=pks).update(game_last=game)


@receiver(pre_save, sender=models.Server)
def update_server_country(sender, instance, **kwargs):
    """Detect and save the server's location (country) by it's IP address prior to the model save."""
    isp, created = models.ISP.objects.match_or_create(instance.ip)
    try:
        assert isp.country
    # country is either empty or the isp is None
    except:
        pass
    else:
        # assign the country
        instance.country = isp.country


@receiver(stream_data_received)
def save_game(sender, data, server, **kwargs):
    """
    Save a Game entry upon receiving data from one of the streaming servers
    Also attempt to save assotiated Objective, Procedures and Player objects, if supplied.
    """
    with transaction.atomic():
        try:
            with transaction.atomic():
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
        except IntegrityError as e:
            logger.warning('the game with tag %s has already been saved' % data['tag'].value)
            return

        players = []
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
                # prepare a Player entry
                player = models.Player(
                    game=game,
                    alias=models.Alias.objects.match_or_create(
                        # prevent empty and coloured names
                        name=utils.force_name(raw_player['name'].value, raw_player['ip'].value),
                        ip=raw_player['ip'].value
                    )[0],
                    ip=raw_player['ip'].value,
                    # team is a mapping, insert a raw value (0 or 1)
                    team=definitions.TEAM_BLUE if game.coop_game else int(raw_player['team'].raw),
                    vip=raw_player['vip'].value,
                    admin=raw_player['admin'].value,
                    dropped=raw_player['dropped'].value,
                    # coop status is also a mapping
                    coop_status=int(raw_player['coop_status'].raw),
                    loadout=models.Loadout.objects.get_or_create(**loadout)[0]
                )
                # insert stats
                for category, key in six.iteritems(STATS):
                    # score, sg_kills, etc
                    if key in raw_player:
                        # set an instance attr with the same name from the raw_player dict
                        setattr(player, key, raw_player[key].value)
                # save the instance
                player.save()
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
def log_game(sender, raw, **kwargs):
    """Save raw stream data into a log file."""
    logging.getLogger('stream').info(raw)
