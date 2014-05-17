# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Player', fields ['alias', 'arrests']
        db.create_index('tracker_player', ['alias_id', 'arrests'])

        # Adding index on 'Player', fields ['alias', 'score']
        db.create_index('tracker_player', ['alias_id', 'score'])

        # Adding index on 'Player', fields ['alias', 'kill_streak']
        db.create_index('tracker_player', ['alias_id', 'kill_streak'])

        # Adding index on 'Player', fields ['alias', 'kills']
        db.create_index('tracker_player', ['alias_id', 'kills'])

        # Adding index on 'Player', fields ['alias', 'arrest_streak']
        db.create_index('tracker_player', ['alias_id', 'arrest_streak'])


    def backwards(self, orm):
        # Removing index on 'Player', fields ['alias', 'arrest_streak']
        db.delete_index('tracker_player', ['alias_id', 'arrest_streak'])

        # Removing index on 'Player', fields ['alias', 'kills']
        db.delete_index('tracker_player', ['alias_id', 'kills'])

        # Removing index on 'Player', fields ['alias', 'kill_streak']
        db.delete_index('tracker_player', ['alias_id', 'kill_streak'])

        # Removing index on 'Player', fields ['alias', 'score']
        db.delete_index('tracker_player', ['alias_id', 'score'])

        # Removing index on 'Player', fields ['alias', 'arrests']
        db.delete_index('tracker_player', ['alias_id', 'arrests'])


    models = {
        'tracker.alias': {
            'Meta': {'object_name': 'Alias', 'index_together': "(('name', 'isp'),)"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isp': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['tracker.ISP']", 'on_delete': 'models.SET_NULL', 'related_name': "'+'"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Profile']"})
        },
        'tracker.game': {
            'Meta': {'object_name': 'Game'},
            'coop_score': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'date_finished': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'gametype': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mapname': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'outcome': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'player_num': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'rd_bombs_defused': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'rd_bombs_total': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'score_sus': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'score_swat': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'server': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['tracker.Server']", 'on_delete': 'models.SET_NULL'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'unique': 'True'}),
            'time': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vict_sus': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vict_swat': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'tracker.ip': {
            'Meta': {'unique_together': "(('range_from', 'range_to'),)", 'object_name': 'IP'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
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
            'Meta': {'object_name': 'Player', 'index_together': "(('alias', 'score'), ('alias', 'kills'), ('alias', 'arrests'), ('alias', 'kill_streak'), ('alias', 'arrest_streak'))"},
            'admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'alias': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Alias']"}),
            'arrest_streak': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'arrested': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'arrests': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_enemy_arrests': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_enemy_incaps': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_enemy_incaps_invalid': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_enemy_kills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_enemy_kills_invalid': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_hostage_arrests': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_hostage_hits': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_hostage_incaps': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_hostage_kills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_status': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'coop_toc_reports': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'death_streak': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'deaths': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'dropped': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'kill_streak': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'kills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'loadout': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['tracker.Loadout']", 'on_delete': 'models.SET_NULL'}),
            'rd_bombs_defused': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'score': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'sg_escapes': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'sg_kills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'suicides': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'team': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'}),
            'teamkills': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vip': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'vip_captures': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vip_escapes': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vip_kills_invalid': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vip_kills_valid': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vip_rescues': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
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
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'}),
            'game_first': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['tracker.Game']", 'on_delete': 'models.SET_NULL', 'related_name': "'+'"}),
            'game_last': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['tracker.Game']", 'on_delete': 'models.SET_NULL', 'related_name': "'+'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'loadout': ('django.db.models.fields.related.ForeignKey', [], {'null': 'True', 'to': "orm['tracker.Loadout']", 'on_delete': 'models.SET_NULL'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'team': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'})
        },
        'tracker.rank': {
            'Meta': {'unique_together': "(('year', 'category', 'profile'),)", 'object_name': 'Rank'},
            'category': ('django.db.models.fields.SmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'position': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'db_index': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Profile']"}),
            'year': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'tracker.server': {
            'Meta': {'unique_together': "(('ip', 'port'),)", 'object_name': 'Server'},
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'listed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'port_gs1': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'port_gs2': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'streamed': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
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