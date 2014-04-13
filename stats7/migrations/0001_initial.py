# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        'stats7.player': {
            'Meta': {'managed': 'False', 'object_name': 'Player', 'db_table': "'player'"},
            'country': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'country_show': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'doppelganger': ('django.db.models.fields.IntegerField', [], {}),
            'enabled': ('django.db.models.fields.IntegerField', [], {}),
            'force_profile': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True', 'db_column': "'player_id'"}),
            'isp': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'profile': ('django.db.models.fields.IntegerField', [], {'db_column': "'profile_id'"})
        },
        'stats7.round': {
            'Meta': {'managed': 'False', 'object_name': 'Round', 'db_table': "'round'"},
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True', 'db_column': "'round_id'"}),
            'map': ('django.db.models.fields.IntegerField', [], {}),
            'numplayers': ('django.db.models.fields.IntegerField', [], {}),
            'reason': ('django.db.models.fields.IntegerField', [], {}),
            'roundend': ('django.db.models.fields.IntegerField', [], {}),
            'roundnum': ('django.db.models.fields.IntegerField', [], {}),
            'roundtime': ('django.db.models.fields.IntegerField', [], {}),
            'server': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'suspectsscore': ('django.db.models.fields.IntegerField', [], {}),
            'suspectswon': ('django.db.models.fields.IntegerField', [], {}),
            'swatscore': ('django.db.models.fields.IntegerField', [], {}),
            'swatwon': ('django.db.models.fields.IntegerField', [], {}),
            'won': ('django.db.models.fields.IntegerField', [], {})
        },
        'stats7.roundplayer': {
            'Meta': {'managed': 'False', 'object_name': 'RoundPlayer', 'db_table': "'round_player'"},
            'arrested': ('django.db.models.fields.IntegerField', [], {}),
            'arrestedvip': ('django.db.models.fields.IntegerField', [], {}),
            'arrests': ('django.db.models.fields.IntegerField', [], {}),
            'deaths': ('django.db.models.fields.IntegerField', [], {}),
            'dropped': ('django.db.models.fields.IntegerField', [], {}),
            'equipment': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'finished': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invalidvipdeaths_sus': ('django.db.models.fields.IntegerField', [], {}),
            'invalidvipdeaths_swat': ('django.db.models.fields.IntegerField', [], {}),
            'invalidvipkills': ('django.db.models.fields.IntegerField', [], {}),
            'ip': ('django.db.models.fields.IntegerField', [], {}),
            'is_sus': ('django.db.models.fields.IntegerField', [], {}),
            'is_swat': ('django.db.models.fields.IntegerField', [], {}),
            'is_vip': ('django.db.models.fields.IntegerField', [], {}),
            'kills': ('django.db.models.fields.IntegerField', [], {}),
            'losses': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['stats7.Player']"}),
            'points': ('django.db.models.fields.IntegerField', [], {}),
            'round': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['stats7.Round']", 'db_column': "'round_id'"}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'time': ('django.db.models.fields.IntegerField', [], {}),
            'tkills': ('django.db.models.fields.IntegerField', [], {}),
            'unarrestedvip': ('django.db.models.fields.IntegerField', [], {}),
            'validvipdeaths': ('django.db.models.fields.IntegerField', [], {}),
            'validvipkills': ('django.db.models.fields.IntegerField', [], {}),
            'vipescaped': ('django.db.models.fields.IntegerField', [], {}),
            'weapons': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'wins': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stats7']