from __future__ import absolute_import
from __future__ import print_function

from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.utils.timezone import now as timezone_now
from zerver.lib.upload import delete_message_image
from zerver.models import (Message, UserMessage, ArchivedMessage, ArchivedUserMessage, Realm,
                           Attachment, ArchivedAttachment)

from typing import Any


@transaction.atomic
def move_expired_rows(src_model, raw_query, **kwargs):
    # type: (Any, str, **Any) -> None
    src_db_table = src_model._meta.db_table
    src_fields = ["{}.{}".format(src_db_table, field.column) for field in src_model._meta.fields]
    dst_fields = [field.column for field in src_model._meta.fields]
    sql_args = {
        'src_fields': ','.join(src_fields),
        'dst_fields': ','.join(dst_fields),
        'archive_timestamp': timezone_now()
    }
    sql_args.update(kwargs)
    with connection.cursor() as cursor:
        cursor.execute(
            raw_query.format(**sql_args)
        )


def move_expired_messages_to_archive(realm):
    # type: (Realm) -> None
    query = """
    INSERT INTO zerver_archivedmessage ({dst_fields}, archive_timestamp)
    SELECT {src_fields}, '{archive_timestamp}'
    FROM zerver_message
    INNER JOIN zerver_userprofile ON zerver_message.sender_id = zerver_userprofile.id
    LEFT JOIN zerver_archivedmessage ON zerver_archivedmessage.id = zerver_message.id
    WHERE zerver_userprofile.realm_id = {realm_id}
          AND  zerver_message.pub_date < '{check_date}'
          AND zerver_archivedmessage.id is NULL
    """
    check_date = timezone_now() - timedelta(days=realm.message_retention_days)
    move_expired_rows(Message, query, realm_id=realm.id, check_date=check_date.isoformat())


def move_expired_user_messages_to_archive(realm):
    # type: (Realm) -> None
    query = """
    INSERT INTO zerver_archivedusermessage ({dst_fields}, archive_timestamp)
    SELECT {src_fields}, '{archive_timestamp}'
    FROM zerver_usermessage
    INNER JOIN zerver_userprofile ON zerver_usermessage.user_profile_id = zerver_userprofile.id
    INNER JOIN zerver_archivedmessage ON zerver_archivedmessage.id = zerver_usermessage.message_id
    LEFT JOIN zerver_archivedusermessage ON zerver_archivedusermessage.id = zerver_usermessage.id
    LEFT JOIN zerver_message ON zerver_usermessage.message_id = zerver_message.id
    WHERE zerver_userprofile.realm_id = {realm_id}
        AND  zerver_message.pub_date < '{check_date}'
        AND zerver_archivedusermessage.id is NULL
    """
    check_date = timezone_now() - timedelta(days=realm.message_retention_days)
    move_expired_rows(UserMessage, query, realm_id=realm.id, check_date=check_date.isoformat())


def move_expired_attachments_to_archive(realm):
    # type: (Realm) -> None
    query = """
       INSERT INTO zerver_archivedattachment ({dst_fields}, archive_timestamp)
       SELECT {src_fields}, '{archive_timestamp}'
       FROM zerver_attachment
       INNER JOIN zerver_attachment_messages ON zerver_attachment_messages.attachment_id = zerver_attachment.id
       INNER JOIN zerver_archivedmessage ON zerver_archivedmessage.id = zerver_attachment_messages.message_id
       LEFT JOIN zerver_archivedattachment ON zerver_archivedattachment.id = zerver_attachment.id
       WHERE zerver_attachment.realm_id = {realm_id}
            AND zerver_archivedattachment.id IS NULL
       GROUP BY zerver_attachment.id
    """
    check_date = timezone_now() - timedelta(days=realm.message_retention_days)
    move_expired_rows(Attachment, query, realm_id=realm.id, check_date=check_date.isoformat())


def move_expired_attachments_message_rows_to_archive(realm):
    # type: (Realm) -> None
    query = """
       INSERT INTO zerver_archivedattachment_messages (id, archivedattachment_id, archivedmessage_id)
       SELECT zerver_attachment_messages.id, zerver_attachment_messages.attachment_id,
           zerver_attachment_messages.message_id
       FROM zerver_attachment_messages
       INNER JOIN zerver_attachment ON zerver_attachment_messages.attachment_id = zerver_attachment.id
       INNER JOIN zerver_message ON zerver_attachment_messages.message_id = zerver_message.id
       LEFT JOIN zerver_archivedattachment_messages ON zerver_archivedattachment_messages.id = zerver_attachment_messages.id
       WHERE zerver_attachment.realm_id = {realm_id}
            AND  zerver_message.pub_date < '{check_date}'
            AND  zerver_archivedattachment_messages.id IS NULL
    """
    check_date = timezone_now() - timedelta(days=realm.message_retention_days)
    with connection.cursor() as cursor:
        cursor.execute(query.format(realm_id=realm.id, check_date=check_date.isoformat()))


def delete_expired_messages(realm):
    # type: (Realm) -> None
    removing_messages = Message.objects.filter(
        usermessage__isnull=True, id__in=ArchivedMessage.objects.all(),
        sender__realm_id=realm.id
    )
    removing_messages.delete()


def delete_expired_user_messages(realm):
    # type: (Realm) -> None
    removing_user_messages = UserMessage.objects.filter(
        id__in=ArchivedUserMessage.objects.all(),
        user_profile__realm_id=realm.id
    )
    removing_user_messages.delete()


def delete_expired_attachments(realm):
    # type: (Realm) -> None
    attachments_to_remove = Attachment.objects.filter(
        messages__isnull=True, id__in=ArchivedAttachment.objects.all(),
        realm_id=realm.id
    )
    attachments_to_remove.delete()


def clean_unused_messages():
    # type: () -> None
    unused_messages = Message.objects.filter(
        usermessage__isnull=True, id__in=ArchivedMessage.objects.all()
    )
    unused_messages.delete()


def archive_messages():
    # type: () -> None
    for realm in Realm.objects.filter(message_retention_days__isnull=False):
        move_expired_messages_to_archive(realm)
        move_expired_user_messages_to_archive(realm)
        move_expired_attachments_to_archive(realm)
        move_expired_attachments_message_rows_to_archive(realm)
        delete_expired_user_messages(realm)
        delete_expired_messages(realm)
        delete_expired_attachments(realm)
    clean_unused_messages()


def delete_expired_archived_attachments_by_realm(realm_id):
    # type: (int) -> None
    expired_date = timezone_now() - timedelta(days=settings.ARCHIVED_DATA_RETENTION_DAYS)
    arc_attachments = ArchivedAttachment.objects \
        .filter(archive_timestamp__lt=expired_date, realm_id=realm_id, messages__isnull=True) \
        .exclude(id__in=Attachment.objects.filter(realm_id=realm_id))
    for arc_att in arc_attachments:
        delete_message_image(arc_att.path_id)
    arc_attachments.delete()


def delete_expired_archived_data_by_realm(realm_id):
    # type: (int) -> None
    arc_expired_date = timezone_now() - timedelta(days=settings.ARCHIVED_DATA_RETENTION_DAYS)
    ArchivedUserMessage.objects.filter(archive_timestamp__lt=arc_expired_date,
                                       user_profile__realm_id=realm_id).delete()
    ArchivedMessage.objects.filter(archive_timestamp__lt=arc_expired_date,
                                   sender__realm_id=realm_id,
                                   archivedusermessage__isnull=True).delete()
    delete_expired_archived_attachments_by_realm(realm_id)

def delete_expired_archived_data():
    # type: () -> None
    for realm in Realm.objects.filter(message_retention_days__isnull=False):
        delete_expired_archived_data_by_realm(realm.id)


def move_attachment_message_to_archive_by_message(message_id):
    # type: (int) -> None
    # Move attachments messages relation table data to archive.
    query = """
        INSERT INTO zerver_archivedattachment_messages (id, archivedattachment_id,
            archivedmessage_id)
        SELECT zerver_attachment_messages.id, zerver_attachment_messages.attachment_id,
            zerver_attachment_messages.message_id
        FROM zerver_attachment_messages
        LEFT JOIN zerver_archivedattachment_messages
            ON zerver_archivedattachment_messages.id = zerver_attachment_messages.id
        WHERE zerver_attachment_messages.message_id = {message_id}
            AND  zerver_archivedattachment_messages.id IS NULL
    """
    with connection.cursor() as cursor:
        cursor.execute(query.format(message_id=message_id))


@transaction.atomic
def move_message_to_archive(message_id):
    # type: (int) -> None
    msg = list(Message.objects.filter(id=message_id).values())
    if not msg:
        raise Message.DoesNotExist
    arc_message = ArchivedMessage(**msg[0])
    arc_message.save()

    # Move user_messages to the archive.
    user_messages = UserMessage.objects.filter(
        message_id=message_id).exclude(id__in=ArchivedUserMessage.objects.all())
    archiving_messages = []
    for user_message in user_messages.values():
        archiving_messages.append(ArchivedUserMessage(**user_message))
    ArchivedUserMessage.objects.bulk_create(archiving_messages)

    # Move attachments to archive
    attachments = Attachment.objects.filter(messages__id=message_id).exclude(
        id__in=ArchivedAttachment.objects.all())
    archiving_attachments = []
    for attachment in attachments.values():
        archiving_attachments.append(ArchivedAttachment(**attachment))
    ArchivedAttachment.objects.bulk_create(archiving_attachments)
    move_attachment_message_to_archive_by_message(message_id)

    # Remove data from main tables
    Message.objects.get(id=message_id).delete()
    user_messages.filter(id__in=ArchivedUserMessage.objects.all(),
                         message_id__isnull=True).delete()
    archived_attachments = ArchivedAttachment.objects.filter(messages__id=message_id)
    Attachment.objects.filter(messages__isnull=True, id__in=archived_attachments).delete()
