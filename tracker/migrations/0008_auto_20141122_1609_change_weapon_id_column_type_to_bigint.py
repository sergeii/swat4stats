from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0007_auto_20141122_1609_change_procedure_id_column_type_to_bigint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='weapon',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]
