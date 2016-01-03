

class ClientIpMiddleware:

    def process_request(self, request):
        if 'X_CLIENT_IP' in request.META:
            request.META['REMOTE_ADDR'] = request.META['X_CLIENT_IP']
