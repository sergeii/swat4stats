# Generated by Django 4.2.4 on 2023-09-05 09:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0007_server_search_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="map",
            name="first_game",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="tracker.game",
            ),
        ),
        migrations.AddField(
            model_name="map",
            name="first_game_played_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="map",
            name="game_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="map",
            name="latest_game",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="tracker.game",
            ),
        ),
        migrations.AddField(
            model_name="map",
            name="latest_game_played_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="map",
            name="rating",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="map",
            name="rating_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
