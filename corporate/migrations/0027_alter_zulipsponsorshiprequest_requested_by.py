# Generated by Django 4.2.7 on 2023-11-28 16:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("corporate", "0026_remove_zulipsponsorshiprequest_realm"),
    ]

    operations = [
        migrations.AlterField(
            model_name="zulipsponsorshiprequest",
            name="requested_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
