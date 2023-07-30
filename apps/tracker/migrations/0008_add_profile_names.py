# Generated by Django 4.1.7 on 2023-07-25 09:31

import django.contrib.postgres.fields
import django.contrib.postgres.search
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_add_alias_search_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='names',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), help_text='Denormalized list of alias names for search vector. Updated by triggers.', null=True, size=None),
        ),
    ]
