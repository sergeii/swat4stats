import logging

from django.db import models


logger = logging.getLogger(__name__)


class MapManager(models.Manager):
    def obtain_for(self, name):
        obj, _ = self.get_or_create(name=name)
        return obj
