# Generated by Django 1.11.20 on 2019-06-05 14:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0228_userprofile_demote_inactive_streams"),
    ]

    operations = [
        migrations.AddField(
            model_name="stream",
            name="message_retention_days",
            field=models.IntegerField(default=None, null=True),
        ),
    ]
