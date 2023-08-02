import cProfile
import pstats
import logging
from io import StringIO
from collections.abc import Callable

from django.http import HttpResponse, HttpRequest
from django.utils.html import format_html


logger = logging.getLogger(__name__)


class RealRemoteAddrMiddleware:
    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        real_remote_addr = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
        if not real_remote_addr:
            logger.warning(
                "unable to detect real remote addr for request; headers: %s", dict(request.META)
            )

        request.META["REAL_REMOTE_ADDR"] = real_remote_addr
        return self.get_response(request)


class ProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request, *args, **kwargs):
        if "debug-profile" not in request.GET:
            return self.get_response(request, *args, **kwargs)

        ordering = request.GET.get("profileby", "cumtime")
        profile = cProfile.Profile()
        profile.enable()
        # profile the entire request-response cycle
        self.get_response(request)

        profile.disable()
        # dump profile stats into human readable format
        out = StringIO()
        (pstats.Stats(profile, stream=out).sort_stats(ordering).print_stats().print_callees())

        report_template = """
        <html>
        <body>
            <pre>{profile_stats}</pre>
        </body>
        </html>
        """
        report_content = format_html(report_template, profile_stats=out.getvalue())
        return HttpResponse(report_content)
