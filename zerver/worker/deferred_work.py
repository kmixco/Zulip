# Documented in https://zulip.readthedocs.io/en/latest/subsystems/queuing.html
import logging
import tempfile
import time
from typing import Any, Dict
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils.timezone import now as timezone_now
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language
from typing_extensions import override

from zerver.actions.message_flags import do_mark_stream_messages_as_read
from zerver.actions.message_send import internal_send_private_message
from zerver.actions.realm_export import notify_realm_export
from zerver.lib.export import export_realm_wrapper
from zerver.lib.push_notifications import clear_push_device_tokens
from zerver.lib.queue import queue_json_publish, retry_event
from zerver.lib.remote_server import (
    PushNotificationBouncerRetryLaterError,
    send_server_data_to_push_bouncer,
)
from zerver.lib.soft_deactivation import reactivate_user_if_soft_deactivated
from zerver.lib.upload import handle_reupload_emojis_event
from zerver.models import Message, Realm, RealmAuditLog, Stream, UserMessage
from zerver.models.users import get_system_bot, get_user_profile_by_id
from zerver.worker.base import QueueProcessingWorker, assign_queue

logger = logging.getLogger(__name__)


@assign_queue("deferred_work")
class DeferredWorker(QueueProcessingWorker):
    """This queue processor is intended for cases where we want to trigger a
    potentially expensive, not urgent, job to be run on a separate
    thread from the Django worker that initiated it (E.g. so we that
    can provide a low-latency HTTP response or avoid risk of request
    timeouts for an operation that could in rare cases take minutes).
    """

    # Because these operations have no SLO, and can take minutes,
    # remove any processing timeouts
    MAX_CONSUME_SECONDS = None

    @override
    def consume(self, event: Dict[str, Any]) -> None:
        start = time.time()
        if event["type"] == "mark_stream_messages_as_read":
            user_profile = get_user_profile_by_id(event["user_profile_id"])
            logger.info(
                "Marking messages as read for user %s, stream_recipient_ids %s",
                user_profile.id,
                event["stream_recipient_ids"],
            )

            for recipient_id in event["stream_recipient_ids"]:
                count = do_mark_stream_messages_as_read(user_profile, recipient_id)
                logger.info(
                    "Marked %s messages as read for user %s, stream_recipient_id %s",
                    count,
                    user_profile.id,
                    recipient_id,
                )
        elif event["type"] == "mark_stream_messages_as_read_for_everyone":
            logger.info(
                "Marking messages as read for all users, stream_recipient_id %s",
                event["stream_recipient_id"],
            )
            stream = Stream.objects.get(recipient_id=event["stream_recipient_id"])
            # This event is generated by the stream deactivation code path.
            batch_size = 50
            start_time = time.perf_counter()
            min_id = event.get("min_id", 0)
            total_messages = 0
            while True:
                with transaction.atomic(savepoint=False):
                    messages = list(
                        Message.objects.filter(
                            # Uses index: zerver_message_realm_recipient_id
                            realm_id=stream.realm_id,
                            recipient_id=event["stream_recipient_id"],
                            id__gt=min_id,
                        )
                        .order_by("id")[:batch_size]
                        .values_list("id", flat=True)
                    )
                    UserMessage.select_for_update_query().filter(message__in=messages).extra(
                        where=[UserMessage.where_unread()]
                    ).update(flags=F("flags").bitor(UserMessage.flags.read))
                total_messages += len(messages)
                if len(messages) < batch_size:
                    break
                min_id = messages[-1]
                if time.perf_counter() - start_time > 30:
                    # This task may take a _very_ long time to
                    # complete, if we have a large number of messages
                    # to mark as read.  If we have taken more than
                    # 30s, we re-push the task onto the tail of the
                    # queue, to allow other deferred work to complete;
                    # this task is extremely low priority.
                    queue_json_publish("deferred_work", {**event, "min_id": min_id})
                    break
            logger.info(
                "Marked %s messages as read for all users, stream_recipient_id %s",
                total_messages,
                event["stream_recipient_id"],
            )
        elif event["type"] == "clear_push_device_tokens":
            logger.info(
                "Clearing push device tokens for user_profile_id %s",
                event["user_profile_id"],
            )
            try:
                clear_push_device_tokens(event["user_profile_id"])
            except PushNotificationBouncerRetryLaterError:

                def failure_processor(event: Dict[str, Any]) -> None:
                    logger.warning(
                        "Maximum retries exceeded for trigger:%s event:clear_push_device_tokens",
                        event["user_profile_id"],
                    )

                retry_event(self.queue_name, event, failure_processor)
        elif event["type"] == "realm_export":
            realm = Realm.objects.get(id=event["realm_id"])
            output_dir = tempfile.mkdtemp(prefix="zulip-export-")
            export_event = RealmAuditLog.objects.get(id=event["id"])
            user_profile = get_user_profile_by_id(event["user_profile_id"])
            extra_data = export_event.extra_data
            if extra_data.get("started_timestamp") is not None:
                logger.error(
                    "Marking export for realm %s as failed due to retry -- possible OOM during export?",
                    realm.string_id,
                )
                extra_data["failed_timestamp"] = timezone_now().timestamp()
                export_event.extra_data = extra_data
                export_event.save(update_fields=["extra_data"])
                notify_realm_export(user_profile)
                return

            extra_data["started_timestamp"] = timezone_now().timestamp()
            export_event.extra_data = extra_data
            export_event.save(update_fields=["extra_data"])

            logger.info(
                "Starting realm export for realm %s into %s, initiated by user_profile_id %s",
                realm.string_id,
                output_dir,
                event["user_profile_id"],
            )

            try:
                public_url = export_realm_wrapper(
                    realm=realm,
                    output_dir=output_dir,
                    threads=1 if self.threaded else 6,
                    upload=True,
                    public_only=True,
                )
            except Exception:
                extra_data["failed_timestamp"] = timezone_now().timestamp()
                export_event.extra_data = extra_data
                export_event.save(update_fields=["extra_data"])
                logging.exception(
                    "Data export for %s failed after %s",
                    user_profile.realm.string_id,
                    time.time() - start,
                    stack_info=True,
                )
                notify_realm_export(user_profile)
                return

            assert public_url is not None

            # Update the extra_data field now that the export is complete.
            extra_data["export_path"] = urlsplit(public_url).path
            export_event.extra_data = extra_data
            export_event.save(update_fields=["extra_data"])

            # Send a direct message notification letting the user who
            # triggered the export know the export finished.
            with override_language(user_profile.default_language):
                content = _(
                    "Your data export is complete. [View and download exports]({export_settings_link})."
                ).format(export_settings_link="/#organization/data-exports-admin")
            internal_send_private_message(
                sender=get_system_bot(settings.NOTIFICATION_BOT, realm.id),
                recipient_user=user_profile,
                content=content,
            )

            # For future frontend use, also notify administrator
            # clients that the export happened.
            notify_realm_export(user_profile)
            logging.info(
                "Completed data export for %s in %s",
                user_profile.realm.string_id,
                time.time() - start,
            )
        elif event["type"] == "reupload_realm_emoji":
            # This is a special event queued by the migration for reuploading emojis.
            # We don't want to run the necessary code in the actual migration, so it simply
            # queues the necessary event, and the actual work is done here in the queue worker.
            realm = Realm.objects.get(id=event["realm_id"])
            logger.info("Processing reupload_realm_emoji event for realm %s", realm.id)
            handle_reupload_emojis_event(realm, logger)
        elif event["type"] == "soft_reactivate":
            logger.info(
                "Starting soft reactivation for user_profile_id %s",
                event["user_profile_id"],
            )
            user_profile = get_user_profile_by_id(event["user_profile_id"])
            reactivate_user_if_soft_deactivated(user_profile)
        elif event["type"] == "push_bouncer_update_for_realm":
            # In the future we may use the realm_id to send only that single realm's info.
            realm_id = event["realm_id"]
            logger.info("Updating push bouncer with metadata on behalf of realm %s", realm_id)
            send_server_data_to_push_bouncer(consider_usage_statistics=False)

        end = time.time()
        logger.info(
            "deferred_work processed %s event (%dms)",
            event["type"],
            (end - start) * 1000,
        )
