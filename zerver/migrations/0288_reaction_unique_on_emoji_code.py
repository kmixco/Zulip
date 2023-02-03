# Generated by Django 2.2.13 on 2020-06-19 08:16

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0287_clear_duplicate_reactions"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="archivedreaction",
            unique_together={
                ("user_profile", "message", "emoji_name"),
                ("user_profile", "message", "reaction_type", "emoji_code"),
            },
        ),
        migrations.AlterUniqueTogether(
            name="reaction",
            unique_together={
                ("user_profile", "message", "emoji_name"),
                ("user_profile", "message", "reaction_type", "emoji_code"),
            },
        ),
    ]
