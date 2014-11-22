# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import tracker.models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Alias',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=64)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('title', models.CharField(max_length=64)),
                ('text', models.TextField()),
                ('signature', models.CharField(max_length=128, blank=True)),
                ('is_published', models.BooleanField(default=False)),
                ('date_published', models.DateTimeField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('tag', models.CharField(unique=True, max_length=8, null=True)),
                ('time', models.SmallIntegerField(default=0)),
                ('outcome', models.SmallIntegerField(default=0)),
                ('gametype', models.SmallIntegerField(null=True)),
                ('mapname', models.SmallIntegerField(null=True)),
                ('player_num', models.SmallIntegerField(default=0)),
                ('score_swat', models.SmallIntegerField(default=0)),
                ('score_sus', models.SmallIntegerField(default=0)),
                ('vict_swat', models.SmallIntegerField(default=0)),
                ('vict_sus', models.SmallIntegerField(default=0)),
                ('rd_bombs_defused', models.SmallIntegerField(default=0)),
                ('rd_bombs_total', models.SmallIntegerField(default=0)),
                ('coop_score', models.SmallIntegerField(default=0)),
                ('date_finished', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model, tracker.models.GameMixin),
        ),
        migrations.CreateModel(
            name='IP',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('range_from', models.BigIntegerField()),
                ('range_to', models.BigIntegerField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ISP',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=255, null=True)),
                ('country', models.CharField(max_length=2, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Loadout',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('primary', models.SmallIntegerField(default=0)),
                ('primary_ammo', models.SmallIntegerField(default=0)),
                ('secondary', models.SmallIntegerField(default=0)),
                ('secondary_ammo', models.SmallIntegerField(default=0)),
                ('equip_one', models.SmallIntegerField(default=0)),
                ('equip_two', models.SmallIntegerField(default=0)),
                ('equip_three', models.SmallIntegerField(default=0)),
                ('equip_four', models.SmallIntegerField(default=0)),
                ('equip_five', models.SmallIntegerField(default=0)),
                ('breacher', models.SmallIntegerField(default=0)),
                ('head', models.SmallIntegerField(default=0)),
                ('body', models.SmallIntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Objective',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.SmallIntegerField()),
                ('status', models.SmallIntegerField(default=0)),
                ('game', models.ForeignKey(to='tracker.Game')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('ip', models.GenericIPAddressField(protocol='IPv4')),
                ('team', models.SmallIntegerField(null=True)),
                ('vip', models.BooleanField(default=False)),
                ('admin', models.BooleanField(default=False)),
                ('dropped', models.BooleanField(default=False)),
                ('coop_status', models.SmallIntegerField(default=0)),
                ('score', models.SmallIntegerField(default=0)),
                ('time', models.SmallIntegerField(default=0)),
                ('kills', models.SmallIntegerField(default=0)),
                ('teamkills', models.SmallIntegerField(default=0)),
                ('deaths', models.SmallIntegerField(default=0)),
                ('suicides', models.SmallIntegerField(default=0)),
                ('arrests', models.SmallIntegerField(default=0)),
                ('arrested', models.SmallIntegerField(default=0)),
                ('kill_streak', models.SmallIntegerField(default=0)),
                ('arrest_streak', models.SmallIntegerField(default=0)),
                ('death_streak', models.SmallIntegerField(default=0)),
                ('vip_captures', models.SmallIntegerField(default=0)),
                ('vip_rescues', models.SmallIntegerField(default=0)),
                ('vip_escapes', models.SmallIntegerField(default=0)),
                ('vip_kills_valid', models.SmallIntegerField(default=0)),
                ('vip_kills_invalid', models.SmallIntegerField(default=0)),
                ('rd_bombs_defused', models.SmallIntegerField(default=0)),
                ('sg_escapes', models.SmallIntegerField(default=0)),
                ('sg_kills', models.SmallIntegerField(default=0)),
                ('coop_hostage_arrests', models.SmallIntegerField(default=0)),
                ('coop_hostage_hits', models.SmallIntegerField(default=0)),
                ('coop_hostage_incaps', models.SmallIntegerField(default=0)),
                ('coop_hostage_kills', models.SmallIntegerField(default=0)),
                ('coop_enemy_arrests', models.SmallIntegerField(default=0)),
                ('coop_enemy_incaps', models.SmallIntegerField(default=0)),
                ('coop_enemy_kills', models.SmallIntegerField(default=0)),
                ('coop_enemy_incaps_invalid', models.SmallIntegerField(default=0)),
                ('coop_enemy_kills_invalid', models.SmallIntegerField(default=0)),
                ('coop_toc_reports', models.SmallIntegerField(default=0)),
                ('alias', models.ForeignKey(to='tracker.Alias')),
                ('game', models.ForeignKey(to='tracker.Game')),
                ('loadout', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='tracker.Loadout', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Procedure',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.SmallIntegerField()),
                ('status', models.CharField(max_length=7)),
                ('score', models.SmallIntegerField(default=0)),
                ('game', models.ForeignKey(to='tracker.Game')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=64, null=True)),
                ('team', models.SmallIntegerField(null=True)),
                ('country', models.CharField(max_length=2, null=True)),
                ('game_first', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='tracker.Game', null=True)),
                ('game_last', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='tracker.Game', null=True)),
                ('loadout', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='tracker.Loadout', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Rank',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('category', models.SmallIntegerField()),
                ('year', models.SmallIntegerField()),
                ('points', models.FloatField(default=0)),
                ('position', models.PositiveIntegerField(db_index=True, null=True)),
                ('profile', models.ForeignKey(to='tracker.Profile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('ip', models.GenericIPAddressField(protocol='IPv4')),
                ('port', models.PositiveIntegerField()),
                ('enabled', models.BooleanField(default=False)),
                ('streamed', models.BooleanField(default=False)),
                ('listed', models.BooleanField(default=False)),
                ('port_gs1', models.PositiveIntegerField(null=True, blank=True)),
                ('port_gs2', models.PositiveIntegerField(null=True, blank=True)),
                ('country', models.CharField(max_length=2, null=True, blank=True)),
                ('hostname', models.CharField(max_length=256, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Weapon',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.SmallIntegerField()),
                ('time', models.SmallIntegerField(default=0)),
                ('shots', models.SmallIntegerField(default=0)),
                ('hits', models.SmallIntegerField(default=0)),
                ('teamhits', models.SmallIntegerField(default=0)),
                ('kills', models.SmallIntegerField(default=0)),
                ('teamkills', models.SmallIntegerField(default=0)),
                ('distance', models.FloatField(default=0)),
                ('player', models.ForeignKey(to='tracker.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='server',
            unique_together=set([('ip', 'port')]),
        ),
        migrations.AlterUniqueTogether(
            name='rank',
            unique_together=set([('year', 'category', 'profile')]),
        ),
        migrations.AlterIndexTogether(
            name='player',
            index_together=set([('alias', 'score'), ('alias', 'arrests'), ('alias', 'kill_streak'), ('alias', 'arrest_streak'), ('alias', 'kills')]),
        ),
        migrations.AddField(
            model_name='ip',
            name='isp',
            field=models.ForeignKey(to='tracker.ISP', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='ip',
            unique_together=set([('range_from', 'range_to')]),
        ),
        migrations.AddField(
            model_name='game',
            name='server',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='tracker.Server', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='alias',
            name='isp',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='tracker.ISP', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='alias',
            name='profile',
            field=models.ForeignKey(to='tracker.Profile'),
            preserve_default=True,
        ),
        migrations.AlterIndexTogether(
            name='alias',
            index_together=set([('name', 'isp')]),
        ),
    ]
