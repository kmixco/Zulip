# Generated by Django 1.10.4 on 2016-12-20 13:45
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0046_realmemoji_author"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="add_emoji_by_admins_only",
            field=models.BooleanField(default=False),
        ),
    ]
