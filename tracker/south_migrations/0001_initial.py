# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Server'
        db.create_table('tracker_server', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ip', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39)),
            ('port', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('streamed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('listed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('port_gs1', self.gf('django.db.models.fields.PositiveIntegerField')(blank=True, null=True)),
            ('port_gs2', self.gf('django.db.models.fields.PositiveIntegerField')(blank=True, null=True)),
            ('country', self.gf('django.db.models.fields.CharField')(blank=True, max_length=2, null=True)),
        ))
        db.send_create_signal('tracker', ['Server'])

        # Adding unique constraint on 'Server', fields ['ip', 'port']
        db.create_unique('tracker_server', ['ip', 'port'])

        # Adding model 'Game'
        db.create_table('tracker_game', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('server', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Server'], on_delete=models.SET_NULL, null=True)),
            ('tag', self.gf('django.db.models.fields.CharField')(max_length=8, null=True, unique=True)),
            ('time', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('outcome', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('gametype', self.gf('django.db.models.fields.SmallIntegerField')(null=True)),
            ('mapname', self.gf('django.db.models.fields.SmallIntegerField')(null=True)),
            ('player_num', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('score_swat', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('score_sus', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('vict_swat', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('vict_sus', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('rd_bombs_defused', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('rd_bombs_total', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_score', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('date_finished', self.gf('django.db.models.fields.DateTimeField')(blank=True, auto_now_add=True)),
        ))
        db.send_create_signal('tracker', ['Game'])

        # Adding model 'Loadout'
        db.create_table('tracker_loadout', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('primary', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('primary_ammo', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('secondary', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('secondary_ammo', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('equip_one', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('equip_two', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('equip_three', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('equip_four', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('equip_five', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('breacher', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('head', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('body', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
        ))
        db.send_create_signal('tracker', ['Loadout'])

        # Adding model 'Weapon'
        db.create_table('tracker_weapon', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('player', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Player'])),
            ('name', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('time', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('shots', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('hits', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('teamhits', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('kills', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('teamkills', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('distance', self.gf('django.db.models.fields.FloatField')(default=0)),
        ))
        db.send_create_signal('tracker', ['Weapon'])

        # Adding model 'Alias'
        db.create_table('tracker_alias', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('profile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Profile'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('isp', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', on_delete=models.SET_NULL, null=True, to=orm['tracker.ISP'])),
        ))
        db.send_create_signal('tracker', ['Alias'])

        # Adding index on 'Alias', fields ['name', 'isp']
        db.create_index('tracker_alias', ['name', 'isp_id'])

        # Adding model 'Player'
        db.create_table('tracker_player', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Game'])),
            ('alias', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Alias'])),
            ('loadout', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Loadout'], on_delete=models.SET_NULL, null=True)),
            ('ip', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39)),
            ('team', self.gf('django.db.models.fields.SmallIntegerField')(null=True)),
            ('vip', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('admin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('dropped', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('coop_status', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('score', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('time', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('kills', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('teamkills', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('deaths', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('suicides', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('arrests', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('arrested', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('kill_streak', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('arrest_streak', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('death_streak', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('vip_captures', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('vip_rescues', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('vip_escapes', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('vip_kills_valid', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('vip_kills_invalid', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('rd_bombs_defused', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('sg_escapes', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('sg_kills', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_hostage_arrests', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_hostage_hits', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_hostage_incaps', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_hostage_kills', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_enemy_arrests', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_enemy_incaps', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_enemy_kills', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_enemy_incaps_invalid', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_enemy_kills_invalid', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('coop_toc_reports', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
        ))
        db.send_create_signal('tracker', ['Player'])

        # Adding model 'Objective'
        db.create_table('tracker_objective', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Game'])),
            ('name', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('status', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
        ))
        db.send_create_signal('tracker', ['Objective'])

        # Adding model 'Procedure'
        db.create_table('tracker_procedure', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Game'])),
            ('name', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=7)),
            ('score', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
        ))
        db.send_create_signal('tracker', ['Procedure'])

        # Adding model 'IP'
        db.create_table('tracker_ip', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('isp', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.ISP'], null=True)),
            ('range_from', self.gf('django.db.models.fields.BigIntegerField')()),
            ('range_to', self.gf('django.db.models.fields.BigIntegerField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(blank=True, auto_now_add=True)),
        ))
        db.send_create_signal('tracker', ['IP'])

        # Adding unique constraint on 'IP', fields ['range_from', 'range_to']
        db.create_unique('tracker_ip', ['range_from', 'range_to'])

        # Adding model 'ISP'
        db.create_table('tracker_isp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=2, null=True)),
        ))
        db.send_create_signal('tracker', ['ISP'])

        # Adding model 'Profile'
        db.create_table('tracker_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True)),
            ('team', self.gf('django.db.models.fields.SmallIntegerField')(null=True)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=2, null=True)),
            ('loadout', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Loadout'], on_delete=models.SET_NULL, null=True)),
            ('game_first', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', on_delete=models.SET_NULL, null=True, to=orm['tracker.Game'])),
            ('game_last', self.gf('django.db.models.fields.related.ForeignKey')(related_name='+', on_delete=models.SET_NULL, null=True, to=orm['tracker.Game'])),
        ))
        db.send_create_signal('tracker', ['Profile'])

        # Adding model 'Rank'
        db.create_table('tracker_rank', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('year', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('profile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Profile'])),
            ('points', self.gf('django.db.models.fields.FloatField')(default=0)),
            ('position', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True, null=True)),
        ))
        db.send_create_signal('tracker', ['Rank'])

        # Adding unique constraint on 'Rank', fields ['year', 'category', 'profile']
        db.create_unique('tracker_rank', ['year', 'category', 'profile_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Rank', fields ['year', 'category', 'profile']
        db.delete_unique('tracker_rank', ['year', 'category', 'profile_id'])

        # Removing unique constraint on 'IP', fields ['range_from', 'range_to']
        db.delete_unique('tracker_ip', ['range_from', 'range_to'])

        # Removing index on 'Alias', fields ['name', 'isp']
        db.delete_index('tracker_alias', ['name', 'isp_id'])

        # Removing unique constraint on 'Server', fields ['ip', 'port']
        db.delete_unique('tracker_server', ['ip', 'port'])

        # Deleting model 'Server'
        db.delete_table('tracker_server')

        # Deleting model 'Game'
        db.delete_table('tracker_game')

        # Deleting model 'Loadout'
        db.delete_table('tracker_loadout')

        # Deleting model 'Weapon'
        db.delete_table('tracker_weapon')

        # Deleting model 'Alias'
        db.delete_table('tracker_alias')

        # Deleting model 'Player'
        db.delete_table('tracker_player')

        # Deleting model 'Objective'
        db.delete_table('tracker_objective')

        # Deleting model 'Procedure'
        db.delete_table('tracker_procedure')

        # Deleting model 'IP'
        db.delete_table('tracker_ip')

        # Deleting model 'ISP'
        db.delete_table('tracker_isp')

        # Deleting model 'Profile'
        db.delete_table('tracker_profile')

        # Deleting model 'Rank'
        db.delete_table('tracker_rank')


    models = {
        'tracker.alias': {
            'Meta': {'index_together': "(('name', 'isp'),)", 'object_name': 'Alias'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isp': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'on_delete': 'models.SET_NULL', 'null': 'True', 'to': "orm['tracker.ISP']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Profile']"})
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
            'server': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Server']", 'on_delete': 'models.SET_NULL', 'null': 'True'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True', 'unique': 'True'}),
            'time': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vict_sus': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'vict_swat': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'})
        },
        'tracker.ip': {
            'Meta': {'object_name': 'IP', 'unique_together': "(('range_from', 'range_to'),)"},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'isp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.ISP']", 'null': 'True'}),
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
            'loadout': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Loadout']", 'on_delete': 'models.SET_NULL', 'null': 'True'}),
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
            'game_first': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'on_delete': 'models.SET_NULL', 'null': 'True', 'to': "orm['tracker.Game']"}),
            'game_last': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'on_delete': 'models.SET_NULL', 'null': 'True', 'to': "orm['tracker.Game']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'loadout': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Loadout']", 'on_delete': 'models.SET_NULL', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'team': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True'})
        },
        'tracker.rank': {
            'Meta': {'object_name': 'Rank', 'unique_together': "(('year', 'category', 'profile'),)"},
            'category': ('django.db.models.fields.SmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'points': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'position': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Profile']"}),
            'year': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'tracker.server': {
            'Meta': {'object_name': 'Server', 'unique_together': "(('ip', 'port'),)"},
            'country': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '2', 'null': 'True'}),
            'enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'listed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'port': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'port_gs1': ('django.db.models.fields.PositiveIntegerField', [], {'blank': 'True', 'null': 'True'}),
            'port_gs2': ('django.db.models.fields.PositiveIntegerField', [], {'blank': 'True', 'null': 'True'}),
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