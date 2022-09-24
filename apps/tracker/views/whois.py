import logging

from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.views import generic

from apps.geoip.models import ISP
from apps.tracker import models
from apps.tracker import schema
from apps.tracker.views.api import StatusAPIViewMixin, KnownServerRequiredMixin, SchemaDataRequiredMixin, APIError

logger = logging.getLogger(__name__)


class APIWhoisView(StatusAPIViewMixin, KnownServerRequiredMixin, SchemaDataRequiredMixin, generic.View):
    schema = schema.whois_schema
    schema_methods = ['get']
    template_name = 'tracker/api/whois/{command}.html'

    def get(self, *args, **kwargs):
        try:
            return self.handle_request()
        except APIError as e:
            raise APIError([self.request_data['command_id'], e.message])

    def handle_request(self):
        """
        Attemp to handle a whois request
        """
        command = self.request_data['command']
        try:
            method = getattr(self, f'handle_{command}')
        except AttributeError:
            logger.error('unknown whois command %s', command,
                         exc_info=True,
                         extra={'data': {'request': self.request_data}})
            raise APIError(_('%(command)s is not a valid command name') % {'command': command})
        else:
            context_data = method(self.request_data.get('args'))

        return [
            self.request_data['command_id'],
            render_to_string(template_name=[self.template_name.format(command=command)],
                             context=context_data,
                             request=self.request)
        ]

    def handle_whois(self, arg):
        """
        Handle a whois command

        :param arg: whois command argument
                    the value is expected to be a player name along with
                    an IP address delimited by \t (tab character)
        """
        try:
            name, ip = arg.split('\t')
        except:
            logger.error('invalid whois args %s', arg)
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
            profile = models.Profile.objects.match_smart(name=name, isp=isp, ip=ip)
        except ObjectDoesNotExist:
            profile = None

        return {
            'name': name,
            'ip': ip,
            'isp': isp.name if isp else None,
            'country': isp.country if isp else None,
            'profile': profile,
        }
