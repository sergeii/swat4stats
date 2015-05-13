from __future__ import unicode_literals

import datetime
import random

from mock import patch
from django import test

from tracker import models, utils, const


class PopularProfileTestCase(test.TestCase):

    unpopular_sets = (
        {},
        {'name': 'Serge', 'country': 'eu'}, 
        {'team': 0},
        {'name': 'Serge', 'team': 0},
    )

    def unpopular_profile_raises_404(self):
        for field_set in self.unpopular_sets:
            response = self.client.get('/profile/%d' % models.Profile.create(**field_set).pk)
            self.assertEqual(response.status_code, 404)
