# Generated by Django 5.0.5 on 2024-05-06 15:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zilencer", "0059_remoterealmauditlog_add_synced_billing_event_type_index"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Django does not provide a RenameConstraint operation.
            # "Constraints" are created as indexes in PostgreSQL, so
            # we rename the underlying indexes.
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER INDEX unique_remote_realm_installation_count "
                        "RENAME TO unique_server_realm_installation_count"
                    ),
                    reverse_sql=(
                        "ALTER INDEX unique_server_realm_installation_count "
                        "RENAME TO unique_remote_realm_installation_count"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER INDEX unique_remote_realm_installation_count_null_subgroup "
                        "RENAME TO unique_server_realm_installation_count_null_subgroup"
                    ),
                    reverse_sql=(
                        "ALTER INDEX unique_server_realm_installation_count_null_subgroup "
                        "RENAME TO unique_remote_realm_installation_count_null_subgroup"
                    ),
                ),
            ],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="remoterealmcount",
                    name="unique_remote_realm_installation_count",
                ),
                migrations.RemoveConstraint(
                    model_name="remoterealmcount",
                    name="unique_remote_realm_installation_count_null_subgroup",
                ),
                migrations.AddConstraint(
                    model_name="remoterealmcount",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(("subgroup__isnull", False)),
                        fields=("server", "realm_id", "property", "subgroup", "end_time"),
                        name="unique_server_realm_installation_count",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="remoterealmcount",
                    constraint=models.UniqueConstraint(
                        condition=models.Q(("subgroup__isnull", True)),
                        fields=("server", "realm_id", "property", "end_time"),
                        name="unique_server_realm_installation_count_null_subgroup",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="remoterealmcount",
            constraint=models.UniqueConstraint(
                condition=models.Q(("subgroup__isnull", False)),
                fields=("remote_realm_id", "property", "subgroup", "end_time"),
                name="unique_remote_realm_installation_count",
            ),
        ),
        migrations.AddConstraint(
            model_name="remoterealmcount",
            constraint=models.UniqueConstraint(
                condition=models.Q(("subgroup__isnull", True)),
                fields=("remote_realm_id", "property", "end_time"),
                name="unique_remote_realm_installation_count_null_subgroup",
            ),
        ),
    ]
