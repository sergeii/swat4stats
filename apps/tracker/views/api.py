import functools
import json
import logging
from enum import Enum
from typing import Any
from collections.abc import Callable

from django.core.exceptions import BadRequest
from django.http import HttpResponse, HttpRequest
from django.utils.translation import gettext_lazy as _
from voluptuous import Invalid

from apps.tracker.models import Server
from apps.tracker.utils.parser import JuliaQueryString


logger = logging.getLogger(__name__)


class APIResponseStatus(str, Enum):
    OK = '0'
    ERROR = '1'


class APIResponse:
    """
    Return an integer status code accompanied by an optional message or a list of messages.
    The status code and the following message(s) are delimited with a new line.

    Example responses:
        1. 0
        2. 0\nData has been accepted
        3. 1\nOutdated mod version\nPlease update to 1.2.3
    """

    @classmethod
    def from_success(cls, message: str | list[str] | None = None) -> HttpResponse:
        return cls._make_response(APIResponseStatus.OK, message)

    @classmethod
    def from_error(cls, message: str | list[str] | None = None) -> HttpResponse:
        return cls._make_response(APIResponseStatus.ERROR, message)

    @classmethod
    def _make_response(cls, status: APIResponseStatus, message: str | list[str] | None) -> HttpResponse:
        parts = [status.value]

        match message:
            case str():
                parts.append(message)
            case list():
                parts.extend(message)

        body = '\n'.join(map(str, parts))
        return HttpResponse(body.strip())


class APIError(BadRequest):

    def __init__(self, message: str | None = None, *args: Any) -> None:
        self.message = message
        super().__init__(*args)


def require_julia_schema(schema: Callable, schema_error_message: str | None = None) -> Callable:
    """
    Decorator to validate request data with specified schema.

    The view input (body or querystring) of a decorated function
    is decoded by the most compatible decoder and is parsed with the specified schema.
    The parsed data is passed as the second argument to the decorated function (after the request).

    In case of validation error, the view returns an error response with the specified error message.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            match request.method:
                case 'POST':
                    request_body = request.body.decode()
                case _:
                    request_body = request.META['QUERY_STRING']

            # json
            match request.META.get('CONTENT_TYPE'):
                case 'application/json':
                    try:
                        decoded_body = json.loads(request_body)
                    except (TypeError, ValueError) as e:
                        logger.exception('failed to parse json request due to %s', e,
                                         extra={'data': {'request': request, 'body': request_body}})
                        return APIResponse.from_error(schema_error_message)
                # legacy formats
                case _:
                    julia_parser = JuliaQueryString()
                    julia_parser.parse(request_body)
                    julia_dotted = any('.' in key for key in julia_parser)
                    expand_func = JuliaQueryString.expand_dots if julia_dotted else JuliaQueryString.expand_array
                    # expand data with either method
                    decoded_body = expand_func(julia_parser)

            try:
                # validate the request data with the specified schema
                request_data = schema(decoded_body)
            except Invalid as e:
                logger.exception('failed to parse game data data due to %s', e,
                                 extra={'data': {'request': request, 'body': request_body}})
                return APIResponse.from_error(schema_error_message)

            return func(request, request_data, *args, **kwargs)

        return wrapper

    return decorator


def require_known_server(func: Callable) -> Callable:
    """
    Decorator to check if the requesting client is known to the tracker.

    The decorated view function checks whether
    there are any listed servers matching the client IP.
    Otherwise, return an error api response
    """
    @functools.wraps(func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        queryset = Server.objects.listed().filter(ip=request.META['REAL_REMOTE_ADDR'])

        if not queryset.exists():
            return APIResponse.from_error([
                _('The server is not allowed to use this service'),
                _('Please check whether it is listed at swat4stats.com/servers')
            ])

        return func(request, *args, **kwargs)

    return wrapper
