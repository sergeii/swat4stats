# Generated by Django 1.9.1 on 2016-01-22 00:23
from django.db import migrations

from apps.tracker.management.commands.fill_last_seen import fill_profile_last_seen


def fill_last_seen(apps, schema_editor):
    Profile = apps.get_model('tracker', 'Profile')
    fill_profile_last_seen(Profile.objects.all())


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('tracker', '0002_fill_server_status_port'),
    ]

    operations = [
        migrations.RunPython(fill_last_seen, atomic=False),
    ]