import logging

from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import generic

from apps.tracker import models
from apps.tracker import schema
from apps.tracker.signals import game_data_received
from apps.tracker.views.api import StatusAPIViewMixin, SchemaDataRequiredMixin, APIError
from apps.utils.misc import flatten_list

logger = logging.getLogger(__name__)


class DataStreamView(StatusAPIViewMixin, SchemaDataRequiredMixin, generic.View):
    schema = schema.game_schema
    schema_error_message = [_(
        'Unable to process the round data due to version mismatch\n'
        'Are you using the latest mod version?\n'
        'If not, please install the latest version from swat4stats.com/install'
    )]

    def get_server(self):
        """
        Attempt to find an existing server for the client IP and the port reported in the request data.
        If none found, create a new instance.

        Raise APIError if the found server is disabled
        """
        attrs = {
            'ip': self.request.META['REAL_REMOTE_ADDR'],
            'port': self.request_data['port'],
        }

        logger.debug('looking for server with ip %s port %s', attrs['ip'], attrs['port'])

        try:
            server = models.Server.objects.get(**attrs)
            logger.debug('obtained server %s for %s', server.pk, server.address)
        except models.Server.DoesNotExist:
            server = models.Server.objects.create_server(**attrs)
            logger.debug('created server %s for %s', server.pk, server.address)

        if not server.enabled:
            logger.debug('server %s (%s) is disabled', server.pk, server.address)
            raise APIError(_('The server is not registered.'))

        return server

    @transaction.atomic
    def post(self, request):
        server = self.get_server()
        logger.debug('received data for %s', server.address)

        messages = []
        errors = []

        # collect messages of the signal handlers
        response = game_data_received.send_robust(sender=None,
                                                  server=server,
                                                  data=self.request_data,
                                                  raw=self.request_body)

        for receiver, result in response:
            if isinstance(result, APIError):
                errors.append(result.message)
            # propagate the exception for proper error handling
            elif isinstance(result, Exception):
                raise result
            else:
                messages.append(result)

            if errors:
                raise APIError(flatten_list(errors))

            return flatten_list(messages)

    def get(self, *args, **kwargs):
        return HttpResponseRedirect('/')
