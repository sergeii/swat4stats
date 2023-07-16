import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic

from apps.geoip.models import ISP
from apps.tracker import models
from apps.tracker import schema
from apps.tracker.exceptions import NoProfileMatch
from apps.tracker.views.api import (
    APIError,
    require_known_server, APIResponse, require_julia_schema,
)

logger = logging.getLogger(__name__)


@method_decorator(require_julia_schema(schema.whois_schema), name='get')
@method_decorator(require_known_server, name='get')
class APIWhoisView(generic.View):
    template_name = 'tracker/api/whois/{command}.html'

    def get(self, request: HttpRequest, whois_args: dict[str, str]) -> HttpResponse:
        try:
            messages = self.handle(whois_args)
        except APIError as exc:
            return APIResponse.from_error([exc.message])
        else:
            return APIResponse.from_success(messages)

    def handle(self, whois_args: dict[str, str]) -> list[str]:
        command = whois_args['command']
        match command:
            case 'whois':
                context_data = self.handle_whois(whois_args.get('args'))
            case _:
                logger.error('unknown whois command %s', command,
                             extra={'data': {'request': whois_args}})
                raise APIError(_('%(command)s is not a valid command name') % {'command': command})

        return [
            whois_args['command_id'],
            render_to_string(template_name=[self.template_name.format(command=command)],
                             context=context_data,
                             request=self.request)
        ]

    def handle_whois(self, arg: str) -> dict[str, Any]:
        """
        Handle a whois command

        :param arg: whois command argument
                    the value is expected to be a player name along with
                    an IP address delimited by \t (tab character)
        """
        try:
            name, ip = arg.split('\t')
        except Exception as exc:
            logger.error('invalid whois args %s: %s', arg, exc)
            raise APIError(_('%(arg)s is not a valid argument for the whois command') % {'arg': arg})

        # get info for the ip addr
        try:
            isp = ISP.objects.match_or_create(ip)[0]
        except ObjectDoesNotExist:
            isp = None
        except ValueError:
            raise APIError(_('%(ip)s is not a valid IP address') % {'ip': ip})

        # attempt to match profile
        try:
            profile = models.Profile.objects.match_smart(name=name, isp=isp, ip_address=ip)
        except NoProfileMatch:
            profile = None

        return {
            'name': name,
            'ip': ip,
            'isp': isp.name if isp else None,
            'country_iso': isp.country if isp else None,
            'profile': profile,
        }
