from django.db import migrations, models
import django.db.models.functions.text


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('tracker', '0004_migrate_mapname_to_map'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='alias',
            index=models.Index(django.db.models.functions.text.Upper('name'), models.F('isp_id'), name='tracker_alias_upper_name_isp_id'),
        ),
        migrations.AddIndex(
            model_name='game',
            index=models.Index(models.OrderBy(models.F('date_finished'), descending=True), name='tracker_game_date_finished_desc'),
        ),
        migrations.AddIndex(
            model_name='game',
            index=models.Index(models.OrderBy(django.db.models.expressions.CombinedExpression(models.F('score_swat'), '+', models.F('score_sus')), descending=True), name='tracker_game_score_swat_score_sus'),
        ),
        migrations.AddIndex(
            model_name='player',
            index=models.Index(models.Func(models.F('ip'), function='host'), models.OrderBy(models.F('id'), descending=True), name='tracker_player_host_ip_id_desc'),
        ),
        migrations.AddIndex(
            model_name='server',
            index=models.Index(models.Func(models.F('ip'), function='host'), models.F('port'), name='tracker_server_host_ip_port'),
        ),
        migrations.AddIndex(
            model_name='playerstats',
            index=models.Index(models.F('year'), models.F('category_legacy'), condition=models.Q(('position__lte', 5)),
                               name='tracker_rank_year_category_position_lte'),
        ),
    ]
