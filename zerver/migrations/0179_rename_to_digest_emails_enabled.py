# Generated by Django 1.11.14 on 2018-08-01 10:59

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0178_rename_to_emails_restricted_to_domains"),
    ]

    operations = [
        migrations.RenameField(
            model_name="realm",
            old_name="show_digest_email",
            new_name="digest_emails_enabled",
        ),
    ]
