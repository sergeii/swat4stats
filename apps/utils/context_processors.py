
def current_view(request):
    if getattr(request, 'resolver_match', None):
        return {
            'current_url_name': request.resolver_match.url_name,
            'current_view_name': request.resolver_match.view_name,
            'current_view_func': '{}.{}'.format(
                request.resolver_match.func.__module__, request.resolver_match.func.__name__
            )
        }
    return {}


def settings(request):
    from django.conf import settings
    return {
        'settings': settings
    }
