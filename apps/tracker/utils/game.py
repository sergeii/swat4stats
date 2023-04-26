from functools import lru_cache

from django.contrib.staticfiles.finders import find as find_static_file
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.text import slugify

from apps.tracker.entities import Equipment, Team


def is_proper_armor(head: Equipment | None, body: Equipment | None,) -> bool:
    match (head, body):
        case (Equipment.helmet | Equipment.gas_mask | Equipment.night_vision_goggles,
              Equipment.light_armor | Equipment.heavy_armor | Equipment.no_armor):
            return True
        case _:
            return False


def get_player_portrait_image(
    team: Team,
    head: Equipment | None,
    body: Equipment | None,
    is_vip: bool = False,
) -> str:
    path_format = 'images/portraits/{name}.jpg'
    if is_vip:
        static_path = path_format.format(name='vip')
    elif is_proper_armor(head, body):
        head_slug = slugify(head.lower())
        body_slug = slugify(body.lower())
        static_path = path_format.format(name=f'{team}-{body_slug}-{head_slug}')
    else:
        static_path = path_format.format(name=f'{team}')
    return static(static_path)


def gametype_rules_text(gametype: str) -> str | None:
    return _gametype_rules_text(gametype)


@lru_cache
def _gametype_rules_text(gametype: str) -> str | None:
    try:
        template_name = f'tracker/includes/rules/{slugify(gametype)}.html'
        return render_to_string(template_name).strip()
    except TemplateDoesNotExist:
        return None


def map_briefing_text(mapname: str) -> str | None:
    return _map_briefing_text(mapname)


@lru_cache
def _map_briefing_text(mapname: str) -> str | None:
    try:
        template_name = f'tracker/includes/briefing/{slugify(mapname)}.html'
        return render_to_string(template_name).strip()
    except TemplateDoesNotExist:
        return None


def map_background_picture(mapname, type='background'):
    return _map_background_picture(mapname, type=type)


@lru_cache
def _map_background_picture(mapname, *, type):
    path_fmt = 'images/maps/%s/{map_slug}.jpg' % type
    map_path = path_fmt.format(map_slug=slugify(mapname))
    # default map is intro
    if not find_static_file(map_path):
        return _intro_background_picture(type)
    return static(map_path)


@lru_cache
def _intro_background_picture(type: str) -> str:
    path = f'images/maps/{type}/intro.jpg'
    return static(path)
