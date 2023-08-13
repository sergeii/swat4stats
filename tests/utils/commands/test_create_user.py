import pytest
from django.contrib.auth.models import User
from django.core.management import call_command


def test_create_user(db):
    opts = {
        "username": "testuser",
        "password": "testpassword",
        "email": "user@example.com",
    }
    call_command("createuser", **opts)

    user = User.objects.get(username="testuser")

    assert user.email == "user@example.com"
    assert user.check_password("testpassword")
    assert user.is_staff is False
    assert user.is_superuser is False


@pytest.mark.parametrize(
    "opt_is_staff, db_is_staff",
    [
        (True, True),
        (False, False),
        (None, False),
    ],
)
def test_create_staff_user(db, opt_is_staff, db_is_staff):
    opts = {
        "username": "testuser",
        "password": "testpassword",
        "email": "user@example.com",
    }
    if opt_is_staff is not None:
        opts["is_staff"] = opt_is_staff

    call_command("createuser", **opts)

    user = User.objects.get(username="testuser")

    assert user.email == "user@example.com"
    assert user.check_password("testpassword")
    assert user.is_staff == db_is_staff
    assert user.is_superuser is False


@pytest.mark.parametrize(
    "opt_is_superuser, db_is_superuser",
    [
        (True, True),
        (False, False),
        (None, False),
    ],
)
def test_create_superuser(db, opt_is_superuser, db_is_superuser):
    opts = {
        "username": "testuser",
        "password": "testpassword",
        "email": "user@example.com",
    }

    if opt_is_superuser is not None:
        opts["is_superuser"] = opt_is_superuser

    call_command("createuser", **opts)

    user = User.objects.get(username="testuser")

    assert user.email == "user@example.com"
    assert user.check_password("testpassword")
    assert user.is_staff == db_is_superuser
    assert user.is_superuser == db_is_superuser
