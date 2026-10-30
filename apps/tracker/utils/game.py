from functools import lru_cache

from django.contrib.staticfiles.finders import find as find_static_file
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.text import slugify


def gametype_rules_text(gametype: str) -> str | None:
    return _gametype_rules_text(gametype)


@lru_cache
def _gametype_rules_text(gametype: str) -> str | None:
    try:
        template_name = f"tracker/includes/rules/{slugify(gametype)}.html"
        return render_to_string(template_name).strip()
    except TemplateDoesNotExist:
        return None


def map_briefing_text(mapname: str) -> str | None:
    return _map_briefing_text(mapname)


@lru_cache
def _map_briefing_text(mapname: str) -> str | None:
    try:
        template_name = f"tracker/includes/briefing/{slugify(mapname)}.html"
        return render_to_string(template_name).strip()
    except TemplateDoesNotExist:
        return None


def map_background_picture(mapname: str, *, style: str = "background") -> str:
    return _map_background_picture(mapname, style=style)


@lru_cache
def _map_background_picture(mapname: str, *, style: str) -> str:
    path_tpl = f"images/maps/{style}/{{map_slug}}.jpg"
    map_path = path_tpl.format(map_slug=slugify(mapname))
    # default map is intro
    if not find_static_file(map_path):
        return _intro_background_picture(style)
    return static(map_path)


@lru_cache
def _intro_background_picture(style: str) -> str:
    path = f"images/maps/{style}/intro.jpg"
    return static(path)
