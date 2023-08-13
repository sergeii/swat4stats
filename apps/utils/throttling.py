from typing import TYPE_CHECKING

from rest_framework.request import Request
from rest_framework.throttling import ScopedRateThrottle

if TYPE_CHECKING:
    from rest_framework.views import APIView


class MethodScopedRateThrottle(ScopedRateThrottle):
    scope_methods_attr = "throttle_scope_methods"

    def allow_request(self, request: Request, view: "APIView") -> bool:
        self.scope_methods = getattr(view, self.scope_methods_attr, None)

        if self.scope_methods and request.method.upper() not in self.scope_methods:
            return True

        return super().allow_request(request, view)
