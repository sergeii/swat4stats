import json
import logging

from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from voluptuous import Invalid

from apps.tracker.models import Server
from apps.tracker.utils.parser import JuliaQueryString


logger = logging.getLogger(__name__)


class APIError(Exception):

    def __init__(self, message=None, *args, **kwargs):
        self.message = message
        super().__init__(*args, **kwargs)


class StatusAPIViewMixin:
    STATUS_OK = '0'
    STATUS_ERROR = '1'

    def dispatch(self, request, *args, **kwargs):
        """
        Return an integer status code accompanied by an optional message.
        The status code and message are delimited with a new line.

        To return an error, simply raise APIError providing it
        an optional error message (or a list of messages)

        Example responses:
            1. 0
            2. 0\nData has been accepted
            3. 1\nOutdated mod version\nPlease update to 1.2.3
        """
        try:
            message = super().dispatch(request, *args, **kwargs)
        except Exception as exc:
            if isinstance(exc, APIError):
                message = exc.message
            else:
                logger.error('error while handling server request %s', exc,
                             exc_info=True,
                             extra={'data': {'request': request}})
                message = _('Failed to accept data due to a server error.')
            status = self.STATUS_ERROR
        else:
            # only handle intermediate response messages
            if isinstance(message, HttpResponse):
                return message
            status = self.STATUS_OK

        # ensure result is a list of messages
        messages = message if isinstance(message, (list, tuple)) else [message]
        return HttpResponse('\n'.join(map(str, filter(None, [status] + list(messages)))))


class SchemaDataRequiredMixin:
    """
    Attempt to parse request data (body POST requests, querystring for the rest methods)
    with specified schema.

    Raise APIError if failed to parse the data.
    """
    schema = None
    schema_methods = ['post']
    schema_error_message = None

    def dispatch(self, request, *args, **kwargs):
        super_ = super().dispatch

        if request.method.lower() not in self.schema_methods:
            return super_(request, *args, **kwargs)

        if request.method in ('POST',):
            request_body = request.body.decode()
        else:
            request_body = request.META['QUERY_STRING']

        # json
        if request.META.get('CONTENT_TYPE') in ('application/json',):
            try:
                request_data = json.loads(request_body)
            except (TypeError, ValueError) as e:
                logger.error('failed to parse json request (%s)', e,
                             exc_info=True,
                             extra={'data': {'request': request,
                                             'body': request_body}})
                error_message = self.schema_error_message
                raise APIError(error_message)
        # old querystring formats
        else:
            julia_parser = JuliaQueryString()
            julia_parser.parse(request_body)
            julia_dotted = any('.' in key for key in julia_parser)
            expand_func = JuliaQueryString.expand_dots if julia_dotted else JuliaQueryString.expand_array
            # expand data with either method
            request_data = expand_func(julia_parser)

        try:
            self.request_body = request_body
            # validate the request data with the specified schema
            self.request_data = self.schema(request_data)
        except Invalid as e:
            logger.error('failed to parse game data data (%s)', e,
                         exc_info=True,
                         extra={'data': {'request': request,
                                         'body': request_body}})
            error_message = self.schema_error_message
            raise APIError(error_message)

        return super_(request, *args, **kwargs)


class KnownServerRequiredMixin:
    """
    Check whether there are any listed servers matching the client IP.

    Raise an APIError if none found.
    """

    def dispatch(self, request, *args, **kwargs):
        queryset = Server.objects.listed().filter(ip=request.META['REAL_REMOTE_ADDR'])

        if not queryset.exists():
            raise APIError(_('The server is not allowed to use this service\n'
                             'Please check whether it is listed at swat4stats.com/servers'))

        return super().dispatch(request, *args, **kwargs)
