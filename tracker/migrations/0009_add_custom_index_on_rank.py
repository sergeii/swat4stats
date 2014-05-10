# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute('CREATE INDEX tracker_rank_year_category_position_lte on tracker_rank (year, category) WHERE position <= 5')

    def backwards(self, orm):
        db.execute('DROP INDEX tracker_rank_year_category_position_lte')