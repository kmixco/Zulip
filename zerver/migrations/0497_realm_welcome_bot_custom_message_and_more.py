# Generated by Django 4.2.9 on 2024-02-13 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0496_alter_scheduledmessage_read_by_sender"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="welcome_bot_custom_message",
            field=models.TextField(default=""),
        ),
        migrations.AddField(
            model_name="realm",
            name="welcome_bot_custom_message_field",
            field=models.BooleanField(default=False),
        ),
    ]
