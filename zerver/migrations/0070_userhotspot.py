# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-28 00:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0069_realmauditlog_extra_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserHotspot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hotspot', models.CharField(max_length=30)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='userhotspot',
            unique_together=set([('user', 'hotspot')]),
        ),
    ]
