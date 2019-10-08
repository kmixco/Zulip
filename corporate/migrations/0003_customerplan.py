# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-22 21:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('corporate', '0002_customer_default_discount'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerPlan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('licenses', models.IntegerField()),
                ('automanage_licenses', models.BooleanField(default=False)),
                ('charge_automatically', models.BooleanField(default=False)),
                ('price_per_license', models.IntegerField(null=True)),
                ('fixed_price', models.IntegerField(null=True)),
                ('discount', models.DecimalField(decimal_places=4, max_digits=6, null=True)),
                ('billing_cycle_anchor', models.DateTimeField()),
                ('billing_schedule', models.SmallIntegerField()),
                ('billed_through', models.DateTimeField()),
                ('next_billing_date', models.DateTimeField(db_index=True)),
                ('tier', models.SmallIntegerField()),
                ('status', models.SmallIntegerField(default=1)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='corporate.Customer')),
            ],
        ),
    ]
