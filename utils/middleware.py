import logging

logger = logging.getLogger(__name__)


class RealRemoteAddrMiddleware:

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        real_remote_addr = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')
        if not real_remote_addr:
            logger.warning('unable to detect real remote addr for request; headers: %s', dict(request.META))
        request.META['REAL_REMOTE_ADDR'] = real_remote_addr
        response = self.get_response(request)
        return response
