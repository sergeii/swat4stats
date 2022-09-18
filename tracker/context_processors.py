def current_view(request):
    resolver_match = getattr(request, 'resolver_match', None)
    if resolver_match:
        return {
            'current_url_name': resolver_match.url_name,
            'current_view_name': resolver_match.view_name,
            'current_view_func': f'{resolver_match.func.__module__}.{resolver_match.func.__name__}',
        }
    return {}
