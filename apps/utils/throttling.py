from rest_framework.throttling import ScopedRateThrottle


class MethodScopedRateThrottle(ScopedRateThrottle):
    scope_methods_attr = "throttle_scope_methods"

    def allow_request(self, request, view):
        self.scope_methods = getattr(view, self.scope_methods_attr, None)

        if self.scope_methods and request.method.upper() not in self.scope_methods:
            return True

        return super().allow_request(request, view)
