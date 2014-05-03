# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class Router(object):

    APP_NAME = 'stats'
    DB_NAME = 'stats'

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.APP_NAME:
            return self.DB_NAME
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.APP_NAME:
            return self.DB_NAME
        return None