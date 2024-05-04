# Generated by Django 4.0.7 on 2022-09-30 20:30

import ast
from typing import List, Tuple, Type

import orjson
from django.db import migrations, transaction
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import F, JSONField, Model
from django.db.models.functions import Cast, JSONObject

# This migration is mostly the same as
# backfill_remote_realmauditlog_extradata_to_json_field in zilencer.

OLD_VALUE = "1"
NEW_VALUE = "2"
USER_FULL_NAME_CHANGED = 124
REALM_DISCOUNT_CHANGED = 209
BATCH_SIZE = 5000

DISCOUNT_DATA_TEMPLATE = """Audit log entry {id} with event type REALM_DISCOUNT_CHANGED is skipped.
The data consistency needs to be manually checked.
  Discount data to remove after the upcoming JSONField migration:
{data_to_remove}
  Discount data to keep after the upcoming JSONField migration:
{data_to_keep}
"""

OVERWRITE_TEMPLATE = """Audit log entry with id {id} has extra_data_json been inconsistently overwritten.
  The old value is:
{old_value}
  The new value is:
{new_value}
"""


@transaction.atomic
def do_bulk_backfill_extra_data(
    audit_log_model: Type[Model], id_lower_bound: int, id_upper_bound: int
) -> None:
    # First handle the special case for audit logs with the
    # USER_FULL_NAME_CHANGED event, which stores the full name not as
    # str(dict()) but a plain str. Note that we only update the entries where
    # extra_data_json has the default value, because we do not want to override
    # existing audit log entries with a NEW_VALUE of None for extra_data_json.
    # We do not need to skip existing entries for other parts of backfilling
    # because we have double-write implemented so that the backfilled value
    # will still be consistent.
    audit_log_model._default_manager.filter(
        event_type=USER_FULL_NAME_CHANGED,
        id__range=(id_lower_bound, id_upper_bound),
        extra_data_json={},
        # extra_data used to keeps track of the old name. As a result, we know
        # nothing about what NEW_VALUE would be especially if the name has been
        # changed multiple times. extra_data_json is a JSONObject whose
        # OLD_VALUE and NEW_VALUE is mapped from the value of the extra_data
        # field (which is just a old full name string) and None, respectively.
        # Documentation for JSONObject:
        # https://docs.djangoproject.com/en/4.2/ref/models/database-functions/#jsonobject
    ).update(extra_data_json=JSONObject(**{OLD_VALUE: "extra_data", NEW_VALUE: None}))

    inconsistent_extra_data_json: List[Tuple[int, str, object, object]] = []
    # A dict converted with str() will start with a open bracket followed by a
    # single quote, as opposed to a JSON-encoded value, which will use a
    # _double_ quote. We use this to filter out those entries with malformed
    # extra_data to be handled later. This should only update rows with
    # extra_data populated with orjson.dumps.

    # The first query below checks for entries that would have extra_data_json
    # being overwritten by the migration with a value inconsistent with its
    # previous value.
    inconsistent_extra_data_json.extend(
        audit_log_model._default_manager.filter(
            extra_data__isnull=False, id__range=(id_lower_bound, id_upper_bound)
        )
        .annotate(new_extra_data_json=Cast("extra_data", output_field=JSONField()))
        .exclude(extra_data__startswith="{'")
        .exclude(event_type=USER_FULL_NAME_CHANGED)
        .exclude(extra_data_json={})
        .exclude(extra_data_json=F("new_extra_data_json"))
        .values_list("id", "extra_data", "extra_data_json", "new_extra_data_json")
    )
    (
        audit_log_model._default_manager.filter(
            extra_data__isnull=False,
            id__range=(id_lower_bound, id_upper_bound),
            extra_data_json__inconsistent_old_extra_data__isnull=True,
        )
        .exclude(extra_data__startswith="{'")
        .exclude(event_type=USER_FULL_NAME_CHANGED)
        .update(extra_data_json=Cast("extra_data", output_field=JSONField()))
    )

    python_valued_audit_log_entries = audit_log_model._default_manager.filter(
        extra_data__startswith="{'",
        id__range=(id_lower_bound, id_upper_bound),
        extra_data_json__inconsistent_old_extra_data__isnull=True,
    )
    for audit_log_entry in python_valued_audit_log_entries:
        # extra_data for entries that store dict stringified with builtins.str()
        # are converted back with ast.literal_eval for safety and efficiency.
        # str()'d extra_data with the REALM_DISCOUNT_CHANGED event type is not
        # handled by this migration. We expect that all such entries are
        # manually converted beforehand or an error will occur during the
        # migration, because ast.literal_eval does not allow the evaluation of
        # Decimal.
        old_value = audit_log_entry.extra_data_json  # type: ignore[attr-defined] # The migration cannot depend on zerver.models, which contains the real type of the RealmAuditLog model, so it cannot be properly typed.
        if audit_log_entry.event_type == REALM_DISCOUNT_CHANGED:  # type: ignore[attr-defined] # Explained above.
            print(
                DISCOUNT_DATA_TEMPLATE.format(
                    id=audit_log_entry.id,  # type: ignore[attr-defined] # Explained above.
                    data_to_remove=audit_log_entry.extra_data,  # type: ignore[attr-defined] # Explained above.
                    data_to_keep=old_value,
                )
            )
            continue
        new_value = ast.literal_eval(audit_log_entry.extra_data)  # type: ignore[attr-defined] # Explained above.
        if old_value not in ({}, new_value):
            inconsistent_extra_data_json.append(
                (audit_log_entry.id, audit_log_entry.extra_data, old_value, new_value)  # type: ignore[attr-defined] # Explained above.
            )
        audit_log_entry.extra_data_json = new_value  # type: ignore[attr-defined] # Explained above.
    audit_log_model._default_manager.bulk_update(
        python_valued_audit_log_entries, fields=["extra_data_json"]
    )

    if inconsistent_extra_data_json:
        audit_log_entries = []
        for (
            audit_log_entry_id,
            old_extra_data,
            old_extra_data_json,
            new_extra_data_json,
        ) in inconsistent_extra_data_json:
            audit_log_entry = audit_log_model._default_manager.get(id=audit_log_entry_id)
            assert isinstance(old_extra_data_json, dict)
            if "inconsistent_old_extra_data" in old_extra_data_json:
                # Skip entries that have been backfilled and detected as
                # anomalies before.
                continue
            assert isinstance(new_extra_data_json, dict)
            audit_log_entry.extra_data_json = {  # type: ignore[attr-defined] # Explained above.
                **new_extra_data_json,
                "inconsistent_old_extra_data": old_extra_data,
                "inconsistent_old_extra_data_json": old_extra_data_json,
            }
            audit_log_entries.append(audit_log_entry)
            print(
                OVERWRITE_TEMPLATE.format(
                    id=audit_log_entry_id,
                    old_value=orjson.dumps(old_extra_data_json).decode(),
                    new_value=orjson.dumps(new_extra_data_json).decode(),
                )
            )
        audit_log_model._default_manager.bulk_update(audit_log_entries, fields=["extra_data_json"])


def backfill_extra_data(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    audit_log_model = apps.get_model("zerver", "RealmAuditLog")
    if not audit_log_model.objects.filter(extra_data__isnull=False).exists():
        return

    audit_log_entries = audit_log_model.objects.filter(extra_data__isnull=False)
    id_lower_bound = audit_log_entries.earliest("id").id
    id_upper_bound = audit_log_entries.latest("id").id
    while id_lower_bound <= id_upper_bound:
        do_bulk_backfill_extra_data(
            audit_log_model, id_lower_bound, min(id_lower_bound + BATCH_SIZE, id_upper_bound)
        )
        id_lower_bound += BATCH_SIZE + 1


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("zerver", "0459_remove_invalid_characters_from_user_group_name"),
    ]

    operations = [
        migrations.RunPython(
            backfill_extra_data, reverse_code=migrations.RunPython.noop, elidable=True
        ),
    ]
