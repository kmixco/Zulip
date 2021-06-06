# Generated by Django 3.1.5 on 2021-02-07 14:56

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import connection, migrations, models
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps


def backfill_is_user_active(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Subscription = apps.get_model("zerver", "Subscription")
    BATCH_SIZE = 1000
    lower_id_bound = 0

    max_id = Subscription.objects.aggregate(models.Max("id"))["id__max"]
    if max_id is None:
        # No Subscription entries
        return
    while lower_id_bound <= max_id:
        print(f"Processed {lower_id_bound} / {max_id}")
        upper_id_bound = lower_id_bound + BATCH_SIZE
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE zerver_subscription
                SET is_user_active = zerver_userprofile.is_active
                FROM zerver_userprofile
                WHERE zerver_subscription.user_profile_id = zerver_userprofile.id
                AND zerver_subscription.id BETWEEN %(lower_id_bound)s AND %(upper_id_bound)s
                """,
                {"lower_id_bound": lower_id_bound, "upper_id_bound": upper_id_bound},
            )

        lower_id_bound += BATCH_SIZE + 1


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("zerver", "0312_subscription_is_user_active"),
    ]

    operations = [
        migrations.RunPython(backfill_is_user_active, reverse_code=migrations.RunPython.noop),
        # Make the field non-null now that we backfilled.
        migrations.AlterField(
            model_name="subscription",
            name="is_user_active",
            field=models.BooleanField(),
        ),
        AddIndexConcurrently(
            model_name="subscription",
            index=models.Index(
                condition=models.Q(("active", True), ("is_user_active", True)),
                fields=["recipient", "user_profile"],
                name="zerver_subscription_recipient_id_user_profile_id_idx",
            ),
        ),
    ]
