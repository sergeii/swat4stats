from django.db import models, migrations
import django.db.models.functions.text


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='alias',
            index=models.Index(django.db.models.functions.text.Upper('name'), models.F('isp_id'),
                               name='tracker_alias_upper_name_isp_id'),
        ),
    ]
