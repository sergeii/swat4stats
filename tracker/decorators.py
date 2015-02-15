# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import datetime
import logging
from functools import wraps

from django.http import Http404
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text, force_bytes
from django.utils import timezone

from julia.node import ValueNodeError
from julia.parse import QueryString

from . import models
from .exceptions import StreamSourceValidationError

logger = logging.getLogger(__name__)


def requires_valid_request(pattern_node):
    """
    Decorate a view with a wrapper that feeds a parsed QueryString instance 
    to the pattern_node's `parse` method.

    In case of success set `stream_data` request attribute 
    (normally a julia.node.DictValueNode instance) that should represent the parsed data.

    In case of failure return an error status response view.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            from .views import StreamView
            # parse request string (either POST body or GET querystring)
            body = force_text(request.body if request.method == 'POST' else request.META['QUERY_STRING'])
            qs = QueryString().parse(body)
            # expand querystring with either method
            qs = (QueryString.expand_dots if any('.' in key for key in qs) else QueryString.expand_array)(qs)
            try:
                # feed the parsed query string
                data = pattern_node.parse(qs)
            except ValueNodeError as e:
                logger.warning(
                    'failed to parse querystring "{}" ({})'.format(body, e),
                    extra={
                        'request': request,
                    }
                )
                # return error status view
                return StreamView.status(
                    request, 
                    StreamView.STATUS_ERROR, 
                    _('Unable to parse data (%(message)s).') % {'message': e},
                )
            else:
                # set request attributes
                setattr(request, 'stream_data', data)
                setattr(request, 'stream_data_raw', body)
                return view(request, *args, **kwargs)
        return wrapped
    return decorator


def requires_authorized_source(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .views import StreamView
        # stream_data should have already been parsed by now
        assert request.stream_data

        attrs = {
            'ip': request.META['REMOTE_ADDR'],
            'port': request.stream_data['port'].value,
        }
        try:
            server = models.Server.objects.get(**attrs)
        except models.Server.DoesNotExist:
            logger.debug('creating a server for {ip}:{port}'.format(**attrs))
            server = models.Server.objects.create_server(enabled=True, streamed=True, **attrs)

        if not server.streamed:
            return StreamView.status(
                request, StreamView.STATUS_ERROR, _('The server is not registered.')
            )

        # store the server instance for further use
        setattr(request, 'stream_source', server)

        return view(request, *args, **kwargs)
    return wrapped


def requires_valid_source(view):
    """
    Decorate a view with a wrapper that attempts to find the client IP in the list of streaming servers.

    In case of success set `stream_source` request attribute pointing to a model instance
    of the matched server and call the original view.

    In case of failure return an error status response.
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .views import StreamView
        try:
            server = (
                models.Server.objects
                .streamed()
                .filter(ip=request.META['REMOTE_ADDR'])[:1]
                .get()
            )
        except models.Server.DoesNotExist:
            logger.warning('server with IP {} is not registered'.format(request.META['REMOTE_ADDR']))
        else:
            # set request attr
            setattr(request, 'stream_source', server)
            return view(request, *args, **kwargs)
        # return error status view instead
        return StreamView.status(request, StreamView.STATUS_ERROR, _('The server is not registered.'))
    return wrapped


def requires_streaming_source(**timedelta_kwargs):
    """
    Decorate a view with with a wrapper that will fail to validate a request from
    a source that has not streamed data to the tracker since `timedelta(**timedelta_kwargs)` ago.

    Args:
        **timedelta_kwargs - kwargs acceptable by the datetime.timedelta constructor (days=n, hours=m, etc)
    """
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            from .views import StreamView
            # calculate min required date
            min_date = timezone.now()-datetime.timedelta(**timedelta_kwargs)

            qs = (models.Game.objects
                .filter(
                    server=request.stream_source,
                    date_finished__gte=min_date
                )[:1]
            )
            # return an error status view in case the server
            # has not streamed for quite a long time
            if not qs.exists():
                return StreamView.status(
                    request,
                    StreamView.STATUS_ERROR,
                    _('The server has been inactive since at least %(date)s.') % {'date': min_date}
                )
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
