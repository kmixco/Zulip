# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-18 20:12
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0063_realm_organization_description'),
    ]

    operations = [
        migrations.RenameField(
            model_name='realm',
            old_name='organization_description',
            new_name='description',
        ),
    ]
