# Generated by Django 4.2.6 on 2023-10-20 00:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zilencer", "0029_update_remoterealm_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="remoteinstallationcount",
            name="remote_id",
            field=models.IntegerField(),
        ),
    ]
