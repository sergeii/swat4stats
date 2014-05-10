# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute('ALTER TABLE tracker_procedure ALTER COLUMN id TYPE bigint')

    def backwards(self, orm):
        db.execute('ALTER TABLE tracker_procedure ALTER COLUMN id TYPE int')