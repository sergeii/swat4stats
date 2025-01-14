from functools import lru_cache

from django.contrib.staticfiles.finders import find as find_static_file
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.text import slugify

from apps.tracker.entities import Equipment, Team


def is_proper_armor(
    head: Equipment | None,
    body: Equipment | None,
) -> bool:
    match (head, body):
        case (
            Equipment.helmet | Equipment.gas_mask | Equipment.night_vision_goggles,
            Equipment.light_armor | Equipment.heavy_armor | Equipment.no_armor,
        ):
            return True
        case _:
            return False


def get_player_portrait_image(
    team: Team | None,
    head: Equipment | None,
    body: Equipment | None,
    *,
    is_vip: bool = False,
) -> str:
    path_format = "images/portraits/{name}.jpg"
    if is_vip:
        static_path = path_format.format(name="vip")
    elif team and is_proper_armor(head, body):
        head_slug = slugify(head.lower())
        body_slug = slugify(body.lower())
        static_path = path_format.format(name=f"{team}-{body_slug}-{head_slug}")
    elif team:
        static_path = path_format.format(name=f"{team}")
    else:
        static_path = path_format.format(name="swat")
    return static(static_path)


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
