import logging
from ipaddress import IPv4Address
from typing import TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction

from apps.geoip.models import ISP

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from apps.tracker.models import Alias


class AliasManager(models.Manager):

    def match_or_create(
        self,
        *,
        name: str,
        ip_address: str | IPv4Address,
    ) -> tuple['Alias', bool]:

        # guard against empty name
        if not name:
            raise ValueError('Empty name')

        isp, _ = ISP.objects.match_or_create(ip_address)

        # attempt to match an existing alias by name+isp pair
        match_kwargs = {
            'name': name,
        }
        # because isp is optional, the only remaining search param is player name
        # therefore if isp is not provided, we need to search against aliases with no isp as well
        if isp:
            match_kwargs['isp'] = isp
        else:
            match_kwargs['isp__isnull'] = True

        match_qs = self.filter(name=name, isp=isp)

        try:
            return match_qs[:1].get(), False
        except ObjectDoesNotExist:
            new_alias = self.create_alias(
                name=name,
                ip_address=ip_address,
                isp=isp,
            )
            return new_alias, True

    @transaction.atomic
    def create_alias(
        self,
        *,
        name: str,
        ip_address: str | IPv4Address,
        isp: ISP | None,
    ) -> 'Alias':
        from apps.tracker.models import Profile

        # get a profile by name and optionally by ip and isp.
        # ISP could as well be empty
        profile, _ = Profile.objects.match_smart_or_create(
            name=name,
            ip_address=ip_address,
            isp=isp,
        )

        return self.create(
            name=name,
            profile=profile,
            profile_name=profile.name,
            isp=isp,
            isp_name=isp.name if isp else None,
            isp_country=isp.country if isp else None,
        )
