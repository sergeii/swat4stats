from ipaddress import IPv4Address
from typing import ClassVar

from django.contrib import admin
from django.db import models
from django.db.models import F
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from apps.geoip.managers import IPManager, ISPManager


class IP(models.Model):
    isp = models.ForeignKey("ISP", null=True, on_delete=models.CASCADE)
    range_from = models.BigIntegerField()
    range_to = models.BigIntegerField()
    date_created = models.DateTimeField(auto_now_add=True)

    objects = IPManager()

    class Meta:
        db_table = "tracker_ip"
        unique_together = (("range_from", "range_to"),)
        indexes: ClassVar[list[models.Index]] = [
            models.Index(F("range_to") - F("range_from"), name="tracker_ip_length"),
        ]

    def __str__(self) -> str:
        return f"{self.range_from_normal}-{self.range_to_normal}"

    @admin.display(description=_("Start"), ordering="range_from")
    @cached_property
    def range_from_normal(self) -> str:
        """Return the range start address in dotted form."""
        return str(IPv4Address(self.range_from))

    @admin.display(description=_("End"), ordering="range_to")
    @cached_property
    def range_to_normal(self):
        """Return the range end address in dotted form."""
        return str(IPv4Address(self.range_to))

    @admin.display(description=_("Length"), ordering="length")
    def admin_length(self):
        return self.length

    @admin.display(description=_("Freshness"), boolean=True, ordering="-date_created")
    def admin_is_fresh(self) -> bool:
        return self.is_fresh


class ISP(models.Model):
    name = models.CharField(max_length=255, null=True)
    country = models.CharField(max_length=2, null=True)
    objects = ISPManager()

    class Meta:
        db_table = "tracker_isp"

    def __str__(self) -> str:
        return f"{self.name}, {self.country}"
