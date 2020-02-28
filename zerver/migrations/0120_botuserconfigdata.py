# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-01 19:12
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0119_userprofile_night_mode'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotUserConfigData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.TextField(db_index=True)),
                ('value', models.TextField()),
                ('bot_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='botuserconfigdata',
            unique_together=set([('bot_profile', 'key')]),
        ),
    ]
