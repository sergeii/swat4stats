from django.utils.translation import gettext_lazy as _
from django_countries import countries as dj_countries

countries = dict(dj_countries.countries)


def country(iso: str | None) -> str:
    if iso:  # noqa: SIM102
        if country_human := countries.get(iso.upper()):
            return country_human
    return _("Terra Incognita")
