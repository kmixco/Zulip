# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-18 19:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0062_default_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='realm',
            name='organization_description',
            field=models.TextField(null=True),
        ),
    ]
