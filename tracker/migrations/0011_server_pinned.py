from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0010_auto_20141122_1612_add_custom_index_on_server'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='pinned',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
