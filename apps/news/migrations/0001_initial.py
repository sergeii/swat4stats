# Generated by Django 1.10.3 on 2016-12-28 19:18

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=64)),
                ('text', models.TextField()),
                ('signature', models.CharField(blank=True, max_length=128)),
                ('is_published', models.BooleanField(default=False)),
                ('date_published', models.DateTimeField(blank=True, default=django.utils.timezone.now)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('renderer', models.SmallIntegerField(choices=[(1, 'Plain text'), (2, 'HTML'), (3, 'Markdown')], default=3)),
            ],
            options={
                'db_table': 'tracker_article',
            },
        ),
    ]
