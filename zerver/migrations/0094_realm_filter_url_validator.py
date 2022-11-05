# Generated by Django 1.11.2 on 2017-07-22 13:44
from django.db import migrations, models

from zerver.models import filter_format_validator


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0093_subscription_event_log_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="realmfilter",
            name="url_format_string",
            field=models.TextField(validators=[filter_format_validator]),
        ),
    ]
