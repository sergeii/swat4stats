# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute('CREATE INDEX tracker_game_date_finished_desc ON tracker_game (date_finished DESC)')
        db.execute('CREATE INDEX tracker_game_score_swat_score_sus ON tracker_game ((score_swat+score_sus) DESC)')

    def backwards(self, orm):
        db.execute('DROP INDEX tracker_game_date_finished_desc')
        db.execute('DROP INDEX tracker_game_score_swat_score_sus')