import logging
from ipaddress import IPv4Address
from typing import TYPE_CHECKING

from django.contrib.postgres.search import SearchVector
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.geoip.models import ISP
from apps.utils.db.func import normalized_names_search_vector

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from apps.tracker.models import Alias


class AliasQuerySet(models.QuerySet):
    def require_search_update(self) -> models.QuerySet["Alias"]:
        return self.filter(
            Q(updated_at__isnull=False),
            Q(search_updated_at__isnull=True) | Q(updated_at__gt=F("search_updated_at")),
        )


class AliasManager(models.Manager):
    def match_or_create(
        self,
        *,
        name: str,
        ip_address: str | IPv4Address,
    ) -> tuple["Alias", bool]:
        # guard against empty name
        if not name:
            raise ValueError("Empty name")

        isp, _ = ISP.objects.match_or_create(ip_address)

        # attempt to match an existing alias by name+isp pair
        match_kwargs = {
            "name": name,
        }
        # because isp is optional, the only remaining search param is player name
        # therefore if isp is not provided, we need to search against aliases with no isp as well
        if isp:
            match_kwargs["isp"] = isp
        else:
            match_kwargs["isp__isnull"] = True

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
    ) -> "Alias":
        from apps.tracker.models import Profile

        # get a profile by name and optionally by ip and isp.
        # ISP could as well be empty
        profile, _ = Profile.objects.match_smart_or_create(
            name=name,
            ip_address=ip_address,
            isp=isp,
        )

        new_alias = self.create(name=name, profile=profile, isp=isp)
        # fmt: off
        logger.info(
            "created alias %s (%d) for profile %s (%d)",
            new_alias, new_alias.pk, profile, profile.pk,
        )
        # fmt: on

        # bump alias_updated_at on profile,
        # so that we can later recalculate the list of unique alias names used by the profile
        updated_at_qs = Profile.objects.filter(
            Q(pk=profile.pk),
            Q(alias_updated_at__isnull=True) | Q(alias_updated_at__lt=new_alias.created_at),
        )
        if updated_at_qs.update(alias_updated_at=new_alias.created_at):
            # fmt: off
            logger.info(
                "bumped alias_updated_at on profile %s (%d) to %s",
                profile, profile.pk, new_alias.created_at,
            )
            # fmt: on
        else:
            # fmt: off
            logger.debug(
                "did not bump alias_updated_at on profile %s (%d) to %s",
                profile, profile.pk, new_alias.created_at,
            )
            # fmt: on

        return new_alias

    @transaction.atomic
    def update_search_vector(self, *alias_ids: int) -> None:
        logger.info("updating search vector for %d aliases", len(alias_ids))

        vector = SearchVector("name", config="simple", weight="A") + normalized_names_search_vector(
            "name", config="simple", weight="B"
        )

        self.filter(pk__in=alias_ids).update(search=vector)
        self.filter(pk__in=alias_ids).update(search_updated_at=timezone.now())
