from django.db import models, migrations
import django.db.models.expressions

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0002_auto_20141122_1551_add_upper_name_index_on_alias'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='game',
            index=models.Index(models.OrderBy(
                django.db.models.expressions.CombinedExpression(models.F('score_swat'), '+', models.F('score_sus')),
                descending=True), name='tracker_game_score_swat_score_sus'),
        ),
        migrations.AddIndex(
            model_name='game',
            index=models.Index(models.OrderBy(models.F('date_finished'), descending=True),
                               name='tracker_game_date_finished_desc'),
        ),
    ]
