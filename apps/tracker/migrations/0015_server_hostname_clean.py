# Generated by Django 4.1.7 on 2023-08-08 20:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0014_server_first_game_server_first_game_played_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="server",
            name="hostname_clean",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
