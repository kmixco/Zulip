# Generated by Django 3.1.7 on 2021-03-31 10:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0318_remove_realm_invite_by_admins_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="realm",
            name="giphy_rating",
            field=models.PositiveSmallIntegerField(default=2),
        ),
    ]
