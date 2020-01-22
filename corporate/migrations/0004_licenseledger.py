# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-01-19 05:01
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corporate', '0003_customerplan'),
    ]

    operations = [
        migrations.CreateModel(
            name='LicenseLedger',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_renewal', models.BooleanField(default=False)),
                ('event_time', models.DateTimeField()),
                ('licenses', models.IntegerField()),
                ('licenses_at_next_renewal', models.IntegerField(null=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='corporate.CustomerPlan')),
            ],
        ),
    ]
