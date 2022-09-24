from django.db import migrations
from django.db.models import F, Q


def fill_status_port(apps, schema_editor):
    Server = apps.get_model('tracker', 'Server')

    (Server.objects
     .filter(Q(status_port__isnull=True) | Q(status_port=0))
     .update(status_port=F('port') + 1))


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fill_status_port)
    ]
