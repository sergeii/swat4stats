from typing import TYPE_CHECKING

from django.db import migrations

from apps.tracker.management.commands.fill_status_port import fill_status_port

if TYPE_CHECKING:
    from django.db.models import Model


def run_fill_status_port(apps, schema_editor):
    server_model: type[Model] = apps.get_model("tracker", "Server")
    fill_status_port(server_model)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("tracker", "0001_initial"),
    ]

    operations = [migrations.RunPython(run_fill_status_port)]
