from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_auto_20141122_1607_change_objective_id_column_type_to_bigint'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='player',
            index=models.Index(models.Func(models.F('ip'), function='host'),
                               models.OrderBy(models.F('id'), descending=True), name='tracker_player_host_ip_id_desc'),
        ),
    ]
