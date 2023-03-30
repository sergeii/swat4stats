# Generated by Django 4.1.1 on 2022-09-23 19:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0006_add_enum_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='objective',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='procedure',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='weapon',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]