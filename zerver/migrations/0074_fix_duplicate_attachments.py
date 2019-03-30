# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-13 22:12

from django.db import migrations
from django.db.backends.postgresql_psycopg2.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import Count

def fix_duplicate_attachments(apps: StateApps, schema_editor: DatabaseSchemaEditor) -> None:
    """Migration 0041 had a bug, where if multiple messages referenced the
    same attachment, rather than creating a single attachment object
    for all of them, we would incorrectly create one for each message.
    This results in exceptions looking up the Attachment object
    corresponding to a file that was used in multiple messages that
    predate migration 0041.

    This migration fixes this by removing the duplicates, moving their
    messages onto a single canonical Attachment object (per path_id).
    """
    Attachment = apps.get_model('zerver', 'Attachment')
    # Loop through all groups of Attachment objects with the same `path_id`
    for group in Attachment.objects.values('path_id').annotate(Count('id')).order_by().filter(id__count__gt=1):
        # Sort by the minimum message ID, to find the first attachment
        attachments = sorted(list(Attachment.objects.filter(path_id=group['path_id']).order_by("id")),
                             key=lambda x: min(x.messages.all().values_list('id')[0]))
        surviving = attachments[0]
        to_cleanup = attachments[1:]
        for a in to_cleanup:
            # For each duplicate attachment, we transfer its messages
            # to the canonical attachment object for that path, and
            # then delete the original attachment.
            for msg in a.messages.all():
                surviving.messages.add(msg)
            surviving.is_realm_public = surviving.is_realm_public or a.is_realm_public
            surviving.save()
            a.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('zerver', '0073_custom_profile_fields'),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_attachments)
    ]
