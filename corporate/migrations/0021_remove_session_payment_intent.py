# Generated by Django 4.2.7 on 2023-11-18 14:54

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("corporate", "0020_add_remote_realm_customers"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="session",
            name="payment_intent",
        ),
    ]
