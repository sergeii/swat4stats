# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute('CREATE INDEX tracker_player_host_ip_id_desc ON tracker_player (HOST(ip), id DESC)')

    def backwards(self, orm):
        db.execute('DROP INDEX tracker_player_host_ip_id_desc')