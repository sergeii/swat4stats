# Generated by Django 4.1.7 on 2023-07-16 12:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_server_merged_into_server_merged_into_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='alias',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='alias',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
