import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction

from apps.geoip.models import ISP


logger = logging.getLogger(__name__)


class AliasManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related()

    def match_or_create(self, defaults=None, **kwargs):
        from apps.tracker.models import Profile
        # name is required for a get_or_create call upon AliasManager
        if 'name' not in kwargs:
            raise ValueError('name is required')
        # use ip for lookup
        ip = kwargs.pop('ip', None)
        # acquire an isp
        if not kwargs.get('isp') and ip:
            kwargs['isp'] = ISP.objects.match_or_create(ip)[0]
        # attempt to match an existing entry by either name or name+isp pair
        alias_filters = kwargs.copy()
        # replace None with notnull lookup
        if 'isp' in alias_filters and not alias_filters['isp']:
            del alias_filters['isp']
            alias_filters['isp__isnull'] = True
        try:
            return self.get_queryset().filter(**alias_filters)[:1].get(), False
        # create a new entry
        except ObjectDoesNotExist:
            with transaction.atomic():
                # get a profile by name and optionally by ip and isp
                # ISP could as well be empty
                if not kwargs.get('profile'):
                    profile_filters = {
                        'name': kwargs['name'],
                        'isp': kwargs.get('isp')
                    }
                    # ip must not be empty
                    if ip:
                        profile_filters['ip'] = ip
                    kwargs['profile'] = Profile.objects.match_smart_or_create(**profile_filters)[0]
                return self.get_queryset().create(**kwargs), True
