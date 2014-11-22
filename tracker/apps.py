# coding: utf-8
from django import apps
 

class AppConfig(apps.AppConfig):
    name = 'tracker'

    def ready(self):
        from . import signals
