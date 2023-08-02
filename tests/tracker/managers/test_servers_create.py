from django.core import exceptions
import pytest

from apps.tracker.models import Server


def test_create_server_valid_port_number(db):
    valid_port_values = (1, "2", 1023, "1024", 10468, 24511, 65535)
    for port in valid_port_values:
        Server.objects.create_server("127.0.0.1", port)


def test_create_server_invalid_port_number(db):
    invalid_port_values = (-1000, -1, "0", 0, 65536, 100000)
    for port in invalid_port_values:
        with pytest.raises(exceptions.ValidationError):
            Server.objects.create_server("127.0.0.1", port)


def test_create_server_duplicate_raises_exception(db):
    Server.objects.create(ip="127.0.0.1", port=10480)
    with pytest.raises(exceptions.ValidationError):
        Server.objects.create_server("127.0.0.1", 10480)
