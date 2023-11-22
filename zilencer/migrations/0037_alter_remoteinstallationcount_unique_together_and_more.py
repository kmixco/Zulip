# Generated by Django 4.2.7 on 2023-11-21 19:08

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zilencer", "0036_remotezulipserver_last_version"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="remoteinstallationcount",
            constraint=models.UniqueConstraint(
                condition=models.Q(("subgroup__isnull", False)),
                fields=("server", "property", "subgroup", "end_time"),
                name="unique_remote_installation_count",
            ),
        ),
        migrations.AddConstraint(
            model_name="remoteinstallationcount",
            constraint=models.UniqueConstraint(
                condition=models.Q(("subgroup__isnull", True)),
                fields=("server", "property", "end_time"),
                name="unique_remote_installation_count_null_subgroup",
            ),
        ),
        migrations.AddConstraint(
            model_name="remoterealmcount",
            constraint=models.UniqueConstraint(
                condition=models.Q(("subgroup__isnull", False)),
                fields=("server", "realm_id", "property", "subgroup", "end_time"),
                name="unique_remote_realm_installation_count",
            ),
        ),
        migrations.AddConstraint(
            model_name="remoterealmcount",
            constraint=models.UniqueConstraint(
                condition=models.Q(("subgroup__isnull", True)),
                fields=("server", "realm_id", "property", "end_time"),
                name="unique_remote_realm_installation_count_null_subgroup",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="remoteinstallationcount",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="remoterealmcount",
            unique_together=set(),
        ),
    ]
