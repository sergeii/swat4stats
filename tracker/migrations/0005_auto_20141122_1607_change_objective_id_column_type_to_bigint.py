from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_auto_20141122_1601_add_ip_length_index'),
    ]

    operations = [
        migrations.AlterField(
            model_name='objective',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]
