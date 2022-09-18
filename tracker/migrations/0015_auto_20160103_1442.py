from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0014_auto_20150513_1519'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alias',
            name='isp',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tracker.ISP'),
        ),
        migrations.AlterField(
            model_name='game',
            name='server',
            field=models.ForeignKey(default=-1, on_delete=django.db.models.deletion.PROTECT, to='tracker.Server'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='player',
            name='loadout',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='tracker.Loadout'),
        ),
        migrations.AlterField(
            model_name='profile',
            name='loadout',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='tracker.Loadout'),
        ),
    ]
