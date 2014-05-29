# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import logging
from functools import wraps
from hashlib import md5

from django.http import Http404
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text, force_bytes

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
                logger.warning('failed to parse querystring ({})'.format(e))
                # return error status view
                return StreamView.status(
                    request, 
                    StreamView.STATUS_ERROR, 
                    _('Unable to parse data from (%(message)s).') % {'message': e},
                )
            else:
                # set request attributes
                setattr(request, 'stream_data', data)
                setattr(request, 'stream_data_raw', body)
                return view(request, *args, **kwargs)
        return wrapped
    return decorator


def requires_authorized_source(view):
    """
    Decorate a view with a wrapper that attemps to find 
    the client IP in the list of streaming servers and challenge it's key hash.

    In case of success set `stream_source` request attribute pointing to a model instance 
    of the matched server and call the original view.

    In case of failure return an error status response.
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .views import StreamView
        # stream_data is required for this decorator
        assert request.stream_data
        try:
            server = (models.Server.objects
                .streamed()
                .get(ip=request.META['REMOTE_ADDR'], port=request.stream_data['port'].value)
            )
            # assemble key test string
            expected_string = ('{}{}{}'
                .format(server.key, server.port, request.stream_data['timestamp'])
            )
            expected_hash = md5(force_bytes(expected_string))
            # validate the last 8 characters of the hash
            if expected_hash.hexdigest()[-8:] != request.stream_data['hash'].value:
                logger.warning(
                    '{} is not valid hash for {}:{} ({})'.format(
                        request.stream_data['hash'].value, 
                        request.META['REMOTE_ADDR'], 
                        request.stream_data['port'].value,
                        request.stream_data['timestamp'],
                    )
                )
                raise StreamSourceValidationError
        except (models.Server.DoesNotExist, StreamSourceValidationError):
            return StreamView.status(request, StreamView.STATUS_ERROR, ('The server is not registered.'))
        else:
            setattr(request, 'stream_source', server)
            return view(request, *args, **kwargs)
    return wrapped


def requires_unique_request(view):
    """
    Decorate a view with a wrapper that rejects duplicate requests.

    The Julia's v2 Tracker extension (along with the HTTP package) is designed 
    the way that it attempts to retry a request if it hasn't receieved 
    a http response in time which makes the tracker prone to receiving duplicate requests.

    In case of a duplicate request return a fake success code.
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .views import StreamView

        qs = models.Game.objects.filter(tag__isnull=False, tag=request.stream_data['tag'].value)

        if qs.exists():
            logger.warning('{} has already been processed'.format(request.stream_data['tag'].value))
            return StreamView.status(request, StreamView.STATUS_OK, _('Received duplicate request.'))

        return view(request, *args, **kwargs)
    return wrapped


def requires_valid_source(view):
    """
    Decorate a view with a wrapper that attemps to find the client IP in the list of streaming servers.

    In case of success set `stream_source` request attribute pointing to a model instance 
    of the matched server and call the original view.

    In case of failure return an error status response.
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .views import StreamView
        try:
            server = (models.Server.objects
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
