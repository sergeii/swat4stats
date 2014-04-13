# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'ServerStatus.gametype'
        db.alter_column('tracker_serverstatus', 'gametype', self.gf('django.db.models.fields.SmallIntegerField')(null=True))

        # Changing field 'ServerStatus.mapname'
        db.alter_column('tracker_serverstatus', 'mapname', self.gf('django.db.models.fields.SmallIntegerField')(null=True))

        # Changing field 'ServerStatus.gamename'
        db.alter_column('tracker_serverstatus', 'gamename', self.gf('django.db.models.fields.SmallIntegerField')(null=True))

        # Changing field 'ServerStatus.hostname'
        db.alter_column('tracker_serverstatus', 'hostname', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'ServerStatus.gamever'
        db.alter_column('tracker_serverstatus', 'gamever', self.gf('django.db.models.fields.CharField')(max_length=5, null=True))

        # Changing field 'Game.mapname'
        db.alter_column('tracker_game', 'mapname', self.gf('django.db.models.fields.SmallIntegerField')(null=True))

        # Changing field 'Game.gametype'
        db.alter_column('tracker_game', 'gametype', self.gf('django.db.models.fields.SmallIntegerField')(null=True))

    def backwards(self, orm):

        # Changing field 'ServerStatus.gametype'
        db.alter_column('tracker_serverstatus', 'gametype', self.gf('django.db.models.fields.SmallIntegerField')())

        # Changing field 'ServerStatus.mapname'
        db.alter_column('tracker_serverstatus', 'mapname', self.gf('django.db.models.fields.SmallIntegerField')())

        # User chose to not deal with backwards NULL issues for 'ServerStatus.gamename'
        raise RuntimeError("Cannot reverse this migration. 'ServerStatus.gamename' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'ServerStatus.gamename'
        db.alter_column('tracker_serverstatus', 'gamename', self.gf('django.db.models.fields.SmallIntegerField')())

        # User chose to not deal with backwards NULL issues for 'ServerStatus.hostname'
        raise RuntimeError("Cannot reverse this migration. 'ServerStatus.hostname' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'ServerStatus.hostname'
        db.alter_column('tracker_serverstatus', 'hostname', self.gf('django.db.models.fields.CharField')(max_length=255))

        # User chose to not deal with backwards NULL issues for 'ServerStatus.gamever'
        raise RuntimeError("Cannot reverse this migration. 'ServerStatus.gamever' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'ServerStatus.gamever'
        db.alter_column('tracker_serverstatus', 'gamever', self.gf('django.db.models.fields.CharField')(max_length=5))

        # Changing field 'Game.mapname'
        db.alter_column('tracker_game', 'mapname', self.gf('django.db.models.fields.SmallIntegerField')())

        # Changing field 'Game.gametype'
        db.alter_column('tracker_game', 'gametype', self.gf('django.db.models.fields.SmallIntegerField')())

    models = {
        'tracker.alias': {
            'Meta': {'index_together': "(('name', 'ip'), ('name', 'isp'))", 'object_name': 'Alias'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'isp': ('django.db.models.fields.related.ForeignKey', [], {'on_delete': 'models.SET_NULL', 'null': 'True', 'to': "orm['tracker.ISP']", 'related_name': "'+'"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'tracker.game': {
            'Meta': {'object_name': 'Game'},
            'coop_score': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'gametype': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapname': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'outcome': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'player_num': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'rd_bombs_defused': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'rd_bombs_total': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'score_sus': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'score_swat': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'on_delete': 'models.SET_NULL', 'null': 'True', 'to': "orm['tracker.Server']"}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '8', 'unique': 'True', 'null': 'True'}),
            'time': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vict_sus': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vict_swat': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'tracker.ip': {
            'Meta': {'object_name': 'IP', 'unique_together': "(('range_from', 'range_to'),)"},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isp': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['tracker.ISP']"}),
            'range_from': ('django.db.models.fields.BigIntegerField', [], {}),
            'range_to': ('django.db.models.fields.BigIntegerField', [], {})
        },
        'tracker.isp': {
            'Meta': {'object_name': 'ISP'},
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'})
        },
        'tracker.loadout': {
            'Meta': {'object_name': 'Loadout'},
            'body': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'breacher': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'equip_five': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'equip_four': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'equip_one': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'equip_three': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'equip_two': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'head': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'primary': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'primary_ammo': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'secondary': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'secondary_ammo': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'tracker.objective': {
            'Meta': {'object_name': 'Objective'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.SmallIntegerField', [], {}),
            'status': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'tracker.player': {
            'Meta': {'object_name': 'Player'},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'alias': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Alias']"}),
            'coop_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'dropped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'loadout': ('django.db.models.fields.related.ForeignKey', [], {'on_delete': 'models.SET_NULL', 'null': 'True', 'to': "orm['tracker.Loadout']"}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Profile']"}),
            'team': ('django.db.models.fields.SmallIntegerField', [], {'default': '-1'}),
            'vip': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'tracker.playerstatus': {
            'Meta': {'object_name': 'PlayerStatus'},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'arrested': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'arrests': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'deaths': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'dropped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Profile']"}),
            'score': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Server']"}),
            'special': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'team': ('django.db.models.fields.SmallIntegerField', [], {'default': '-1'}),
            'vip': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'tracker.procedure': {
            'Meta': {'object_name': 'Procedure'},
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.SmallIntegerField', [], {}),
            'score': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '7'})
        },
        'tracker.profile': {
            'Meta': {'object_name': 'Profile'},
            'count_views': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'}),
            'date_played': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'date_viewed': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'loadout': ('django.db.models.fields.related.ForeignKey', [], {'on_delete': 'models.SET_NULL', 'null': 'True', 'to': "orm['tracker.Loadout']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'team': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'})
        },
        'tracker.rank': {
            'Meta': {'index_together': "(('year', 'category'),)", 'object_name': 'Rank', 'unique_together': "(('year', 'profile', 'category'),)"},
            'category': ('django.db.models.fields.SmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'position': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Profile']"}),
            'year': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'tracker.score': {
            'Meta': {'object_name': 'Score'},
            'category': ('django.db.models.fields.SmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Player']"}),
            'points': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'tracker.server': {
            'Meta': {'object_name': 'Server', 'unique_together': "(('ip', 'port'),)"},
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'port': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'tracker.serverstatus': {
            'Meta': {'object_name': 'ServerStatus'},
            'coop_score': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'gamename': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'gametype': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'gamever': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True'}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapname': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'passworded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'player_max': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'player_num': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'rd_bombs_defused': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'rd_bombs_total': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'round_max': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'round_num': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'score_sus': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'score_swat': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'server': ('django.db.models.fields.related.OneToOneField', [], {'unique': 'True', 'to': "orm['tracker.Server']", 'related_name': "'status'"}),
            'time': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'vict_sus': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vict_swat': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'tracker.weapon': {
            'Meta': {'object_name': 'Weapon'},
            'distance': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'hits': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.SmallIntegerField', [], {}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Player']"}),
            'shots': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'teamhits': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'teamkills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['tracker']