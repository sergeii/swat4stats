# Generated by Django 4.1.7 on 2023-08-10 11:14

import django.contrib.postgres.search
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0006_alias_search_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="server",
            name="first_game",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="tracker.game",
            ),
        ),
        migrations.AddField(
            model_name="server",
            name="first_game_played_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="server",
            name="game_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="server",
            name="hostname_clean",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name="server",
            name="hostname_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="server",
            name="latest_game",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="tracker.game",
            ),
        ),
        migrations.AddField(
            model_name="server",
            name="latest_game_played_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="server",
            name="search",
            field=django.contrib.postgres.search.SearchVectorField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="server",
            name="search_updated_at",
            field=models.DateTimeField(null=True),
        ),
    ]
