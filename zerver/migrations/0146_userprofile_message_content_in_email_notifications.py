# Generated by Django 1.11.6 on 2017-11-29 12:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0145_reactions_realm_emoji_name_to_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="message_content_in_email_notifications",
            field=models.BooleanField(default=True),
        ),
    ]
