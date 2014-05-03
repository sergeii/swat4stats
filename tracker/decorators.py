# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import logging
from functools import wraps
from hashlib import md5

from django.http import Http404
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text, force_bytes

from julia.node import ValueNodeError
from julia.shortcuts import julia_v2

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
            # get a QueryStringParser instance with dots expanded
            qs = julia_v2(force_text(request.body))
            logger.debug(
                'requires_valid_request: parsed querystring from {}...'.format(request.body[:40])
            )
            try:
                # feed the parsed query string
                data = pattern_node.parse(qs)
            except ValueNodeError as e:
                logger.warning(
                    'requires_valid_request: failed to map querystring ({})'.format(e)
                )
                # return error status view
                return StreamView.status(
                    request,
                    StreamView.STATUS_ERROR,
                    _('Failed to parse request data (%(message)s).') % {'message': e}
                )
            else:
                setattr(request, 'stream_data', data)
                return view(request, *args, **kwargs)
        return wrapped
    return decorator


def requires_valid_source(view):
    """
    Decorate a view with a wrapper that validates 
    succefully parsed stream data against the list of registered servers.

    In case of success set `stream_source` request attribute pointing to a model instance 
    of the matched server and return the original view.

    In case of failure return an error status response view.
    """
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .views import StreamView
        error = None
        try:
            server = models.Server.objects.streamed().get(
                ip=request.META['REMOTE_ADDR'], port=request.stream_data['port'].value
            )
            # assemble an md5 hash test value
            hash = md5(
                force_bytes('{}{}{}'.format(server.key, server.port, request.stream_data['timestamp']))
            )
            # validate the last 8 characters of the hash
            if hash.hexdigest()[-8:] != request.stream_data['hash'].value:
                logger.info(
                    'requires_valid_source: {} is not valid hash for {}:{} ({})'.format(
                        request.stream_data['hash'].value, 
                        request.META['REMOTE_ADDR'], 
                        request.stream_data['port'].value,
                        request.stream_data['timestamp'],
                    )
                )
                raise StreamSourceValidationError(_('Failed to authenticate the server.'))
        except models.Server.DoesNotExist:
            logger.info(
                'requires_valid_source: failed to retrieve {}:{}'.format(
                    request.META['REMOTE_ADDR'], request.stream_data['port'].value
                )
            )
            error = _('The server is not registered.')
        except StreamSourceValidationError as e:
            error = str(e)
        else:
            setattr(request, 'stream_source', server)
            return view(request, *args, **kwargs)
        # return error status view instead
        return StreamView.status(request, StreamView.STATUS_ERROR, error)
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
        if models.Game.objects.filter(tag__isnull=False, tag=request.stream_data['tag'].value).exists():
            logger.warning(
                'requires_unique_request: {} has already been processed'.format(
                    request.stream_data['tag'].value,
                )
            )
            return StreamView.status(request, StreamView.STATUS_OK, _('Received duplicate request.'))
        return view(request, *args, **kwargs)
    return wrapped