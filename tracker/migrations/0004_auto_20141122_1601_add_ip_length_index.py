from django.db import models, migrations
import django.db.models.expressions

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_auto_20141122_1558_add_functional_index_on_game'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='ip',
            index=models.Index(
                django.db.models.expressions.CombinedExpression(models.F('range_to'), '-', models.F('range_from')),
                name='tracker_ip_length'),
        ),
    ]
