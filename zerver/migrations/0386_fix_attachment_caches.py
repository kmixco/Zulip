# Generated by Django 3.2.12 on 2022-03-23 04:32

from django.db import migrations, models
from django.db.backends.postgresql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import Exists, Model, OuterRef


def fix_attachment_caches(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    Attachment = apps.get_model("zerver", "Attachment")
    ArchivedAttachment = apps.get_model("zerver", "ArchivedAttachment")
    Message = apps.get_model("zerver", "Message")
    ArchivedMessage = apps.get_model("zerver", "ArchivedMessage")

    BATCH_SIZE = 10000

    def update_batch(attachment_model: Model, message_model: Model, lower_bound: int) -> None:
        attachment_model.objects.filter(
            id__gt=lower_bound, id__lte=lower_bound + BATCH_SIZE
        ).update(
            is_web_public=Exists(
                message_model.objects.filter(
                    attachment=OuterRef("id"),
                    recipient__stream__invite_only=False,
                    recipient__stream__is_web_public=True,
                ),
            ),
            is_realm_public=Exists(
                message_model.objects.filter(
                    attachment=OuterRef("id"),
                    recipient__stream__invite_only=False,
                )
            ),
        )

    max_id = Attachment.objects.aggregate(models.Max("id"))["id__max"]
    if max_id is not None:
        lower_bound = 0

        while lower_bound < max_id:
            print(f"Processed {lower_bound}/{max_id} attachments.")
            update_batch(Attachment, Message, lower_bound)
            lower_bound += BATCH_SIZE

    max_id = ArchivedAttachment.objects.aggregate(models.Max("id"))["id__max"]
    if max_id is not None:
        lower_bound = 0

        while lower_bound < max_id:
            print(f"Processed {lower_bound}/{max_id} archived attachments.")
            update_batch(ArchivedAttachment, ArchivedMessage, lower_bound)
            lower_bound += BATCH_SIZE


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("zerver", "0385_attachment_flags_cache"),
    ]

    operations = [
        migrations.AlterField(
            model_name="archivedattachment",
            name="messages",
            field=models.ManyToManyField(
                related_name="attachment_set",
                related_query_name="attachment",
                to="zerver.ArchivedMessage",
            ),
        ),
        migrations.RunPython(fix_attachment_caches, reverse_code=migrations.RunPython.noop),
    ]
