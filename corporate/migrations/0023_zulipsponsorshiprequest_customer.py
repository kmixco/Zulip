# Generated by Django 4.2.7 on 2023-11-26 16:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("corporate", "0022_session_is_manual_license_management_upgrade_session"),
    ]

    operations = [
        migrations.AddField(
            model_name="zulipsponsorshiprequest",
            name="customer",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE, to="corporate.customer"
            ),
        ),
    ]
