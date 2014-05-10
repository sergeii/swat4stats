# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.execute('CREATE INDEX tracker_server_host_ip_port ON tracker_server (HOST(ip), port)')

    def backwards(self, orm):
        db.execute('DROP INDEX tracker_server_host_ip_port')