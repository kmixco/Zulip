# Generated by Django 4.0.7 on 2022-10-02 17:02

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("zerver", "0466_realmfilter_order"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="realmauditlog",
            name="extra_data",
        ),
        migrations.RenameField(
            model_name="realmauditlog",
            old_name="extra_data_json",
            new_name="extra_data",
        ),
    ]
