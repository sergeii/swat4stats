from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0013_article_renderer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='date_published',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='article',
            name='title',
            field=models.CharField(max_length=64, blank=True),
        ),
    ]
