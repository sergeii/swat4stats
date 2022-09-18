from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0009_auto_20141122_1611_add_custom_index_on_rank'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='server',
            index=models.Index(models.Func(models.F('ip'), function='host'), models.F('port'),
                               name='tracker_server_host_ip_port'),
        ),
    ]
