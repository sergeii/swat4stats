def test_client_ip_overwrites_remote_addr(db, client):
    response = client.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='1.1.1.1')
    assert response.wsgi_request.META['REAL_REMOTE_ADDR'] == '1.1.1.1'


def test_remote_addr_is_retained(db, client):
    response = client.get('/', REMOTE_ADDR='127.0.0.1')
    assert response.wsgi_request.META['REAL_REMOTE_ADDR'] == '127.0.0.1'
