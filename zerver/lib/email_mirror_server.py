import base64
import email
import logging
import smtplib
from typing import List

from aiosmtpd.handlers import Message as MessageHandler
from aiosmtpd.smtp import SMTP, Envelope, Session
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.mail import EmailMultiAlternatives as DjangoEmailMultiAlternatives

from zerver.lib.email_mirror import (
    decode_stream_email_address,
    is_missed_message_address,
    rate_limit_mirror_by_realm,
    validate_to_address,
)
from zerver.lib.email_mirror_helpers import (
    ZulipEmailForwardError,
    get_email_gateway_message_string_from_address,
)
from zerver.lib.exceptions import RateLimitedError
from zerver.lib.queue import queue_json_publish

logger = logging.getLogger("zulip.email_mirror_server")
# log_to_file(logger, settings.EMAIL_MIRROR_LOG_PATH)


def send_to_postmaster(msg: email.message.Message) -> None:
    # RFC5321 says:
    #   Any system that includes an SMTP server supporting mail relaying or
    #   delivery MUST support the reserved mailbox "postmaster" as a case-
    #   insensitive local name.  This postmaster address is not strictly
    #   necessary if the server always returns 554 on connection opening (as
    #   described in Section 3.1).  The requirement to accept mail for
    #   postmaster implies that RCPT commands that specify a mailbox for
    #   postmaster at any of the domains for which the SMTP server provides
    #   mail service, as well as the special case of "RCPT TO:<Postmaster>"
    #   (with no domain specification), MUST be supported.
    #
    # We forward such mail to the ZULIP_ADMINISTRATOR
    mail = DjangoEmailMultiAlternatives(
        subject=f"Mail to postmaster: {msg['Subject']}",
        from_email=settings.NOREPLY_EMAIL_ADDRESS,
        to=[settings.ZULIP_ADMINISTRATOR],
    )
    mail.attach(None, msg, "message/rfc822")
    try:
        mail.send()
    except smtplib.SMTPResponseException as e:
        logger.exception(
            "Error sending bounce email to %s with error code %s: %s",
            mail.to,
            e.smtp_code,
            e.smtp_error,
            stack_info=True,
        )
    except smtplib.SMTPException as e:
        logger.exception("Error sending bounce email to %s: %s", mail.to, str(e), stack_info=True)


class ZulipMessageHandler(MessageHandler):
    def __init__(self) -> None:
        super().__init__(email.message.Message)

    async def handle_RCPT(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        address: str,
        rcpt_options: List[str],
    ) -> str:
        # Rewrite all postmaster email addresses to just "postmaster"
        if address.lower() == "postmaster":
            envelope.rcpt_tos.append("postmaster")
            return "250 Continue"
        try:
            if get_email_gateway_message_string_from_address(address).lower() == "postmaster":
                envelope.rcpt_tos.append("postmaster")
                return "250 Continue"
        except ZulipEmailForwardError:
            pass

        try:
            await sync_to_async(validate_to_address)(address)
            if not is_missed_message_address(address):
                # Missed message addresses are one-time use, so we don't need
                # to worry about emails to them resulting in message spam.
                recipient_realm = await sync_to_async(
                    lambda a: decode_stream_email_address(a)[0].realm
                )(address)
                rate_limit_mirror_by_realm(recipient_realm)
        except RateLimitedError:
            logger.warning(
                "Rejecting a MAIL FROM: %s to realm: %s - rate limited.",
                envelope.mail_from,
                recipient_realm.name,
            )
            return "550 4.7.0 Rate-limited due to too many emails on this realm."

        except ZulipEmailForwardError as e:
            return f"550 5.1.1 Bad destination mailbox address: {e}"

        envelope.rcpt_tos.append(address)
        return "250 Continue"

    async def handle_DATA(self, server: SMTP, session: Session, envelope: Envelope) -> str:
        message = self.prepare_message(session, envelope)

        msg_base64 = base64.b64encode(bytes(message))
        for address in envelope.rcpt_tos:
            if address == "postmaster":
                send_to_postmaster(message)
            else:
                await sync_to_async(queue_json_publish)(
                    "email_mirror",
                    {
                        "rcpt_to": address,
                        "msg_base64": msg_base64.decode(),
                    },
                )

        return "250 OK"

    # This is never called, as we override handle_DATA, above, because
    # we need access to the envelope; but it must be defined, as
    # Message defines it as an abstract method.
    def handle_message(self, message: email.message.Message) -> None:
        pass
