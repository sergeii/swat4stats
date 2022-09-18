from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0008_auto_20141122_1609_change_weapon_id_column_type_to_bigint'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='rank',
            index=models.Index(models.F('year'), models.F('category'), condition=models.Q(('position__lte', 5)),
                               name='tracker_rank_year_category_position_lte'),
        ),
    ]
