# Generated by Django 3.2 on 2021-05-07 14:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("zilencer", "0021_remove_remoterealmauditlog_extra_data"),
    ]

    operations = [
        migrations.RenameField(
            model_name="remoterealmauditlog",
            old_name="extra_data_json",
            new_name="extra_data",
        ),
    ]
