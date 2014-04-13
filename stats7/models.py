# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Player(models.Model):
    id = models.IntegerField(primary_key=True, db_column='player_id')
    profile = models.IntegerField(db_column='profile_id')
    name = models.CharField(max_length=30)
    isp = models.CharField(max_length=30)
    country = models.CharField(max_length=2)
    country_show = models.CharField(max_length=2)
    enabled = models.IntegerField()
    doppelganger = models.IntegerField()
    force_profile = models.IntegerField()

    def __str__(self):
        return '{0.name}, {0.isp} {0.country}/{0.country_show}'.format(self)

    class Meta:
        managed = True
        db_table = 'player'


@python_2_unicode_compatible
class Round(models.Model):
    id = models.IntegerField(primary_key=True, db_column='round_id')
    server = models.CharField(max_length=4)
    roundend = models.IntegerField()
    roundtime = models.IntegerField()
    reason = models.IntegerField()
    roundnum = models.IntegerField()
    map = models.IntegerField()
    numplayers = models.IntegerField()
    won = models.IntegerField()
    swatwon = models.IntegerField()
    suspectswon = models.IntegerField()
    swatscore = models.IntegerField()
    suspectsscore = models.IntegerField()

    def __str__(self):
        return '{}/{} on {} at {} ({}:{})'.format(
            self.numplayers, '16', self.map,
            self.roundend, self.swatscore, self.suspectsscore)

    class Meta:
        managed = True
        db_table = 'round'


@python_2_unicode_compatible
class RoundPlayer(models.Model):
    round = models.ForeignKey('Round', db_column='round_id')
    player = models.ForeignKey('Player')
    ip = models.PositiveIntegerField()
    dropped = models.IntegerField()
    finished = models.IntegerField()
    time = models.IntegerField()
    points = models.IntegerField()
    score = models.IntegerField()
    is_swat = models.IntegerField()
    is_vip = models.IntegerField()
    is_sus = models.IntegerField()
    wins = models.IntegerField(blank=True, null=True)
    losses = models.IntegerField(blank=True, null=True)
    kills = models.IntegerField()
    tkills = models.IntegerField()
    deaths = models.IntegerField()
    arrests = models.IntegerField()
    arrested = models.IntegerField()
    validvipkills = models.IntegerField()
    validvipdeaths = models.IntegerField()
    invalidvipdeaths_swat = models.IntegerField()
    invalidvipdeaths_sus = models.IntegerField()
    invalidvipkills = models.IntegerField()
    vipescaped = models.IntegerField()
    arrestedvip = models.IntegerField()
    unarrestedvip = models.IntegerField()
    equipment = models.CharField(max_length=9)
    weapons = models.CharField(max_length=12)


    def __str__(self):
        return '{} {}'.format(self.player_id, self.ip)

    class Meta:
        managed = True
        db_table = 'round_player'