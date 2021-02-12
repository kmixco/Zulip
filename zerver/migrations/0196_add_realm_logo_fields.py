# Generated by Django 1.11.14 on 2018-08-16 00:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0195_realm_first_visible_message_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="logo_source",
            field=models.CharField(
                choices=[("D", "Default to Zulip"), ("U", "Uploaded by administrator")],
                default="D",
                max_length=1,
            ),
        ),
        migrations.AddField(
            model_name="realm",
            name="logo_version",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
