import argparse
from typing import Any

from django.contrib.auth.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Create a user"  # noqa: A003

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--is-superuser", action="store_true", default=False)
        parser.add_argument("--is-staff", action="store_true", default=False)

    def handle(self, *args: Any, **options: Any) -> None:
        user = User.objects.create_user(
            options["username"],
            email=options["email"],
            password=options["password"],
            is_staff=options["is_staff"] or options["is_superuser"],
            is_superuser=options["is_superuser"],
        )
        self.stdout.write(
            f"Successfully created user {user.username} "
            f"(is_staff:{user.is_staff}, is_superuser:{user.is_superuser})"
        )
