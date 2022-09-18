from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_auto_20141122_1608_add_custom_index_on_player'),
    ]

    operations = [
        migrations.AlterField(
            model_name='procedure',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        )
    ]
