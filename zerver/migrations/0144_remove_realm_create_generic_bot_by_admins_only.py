# Generated by Django 1.11.6 on 2018-03-09 21:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("zerver", "0143_realm_bot_creation_policy"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="realm",
            name="create_generic_bot_by_admins_only",
        ),
    ]
