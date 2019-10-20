# Webhooks for external integrations.
from typing import Any, Dict, Optional, Callable

from django.db.models import Q
from django.http import HttpRequest, HttpResponse

from zerver.decorator import api_key_only_webhook_view
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_success
from zerver.lib.webhooks.common import check_send_webhook_message, \
    UnexpectedWebhookEventType
from zerver.models import Realm, UserProfile

IGNORED_EVENTS = [
    "downloadChart",
    "deleteChart",
    "uploadChart",
    "pullImage",
    "deleteImage",
    "scanningFailed"
]


def guess_zulip_user_from_harbor(harbor_username: str, realm: Realm) -> Optional[UserProfile]:
    try:
        # Try to find a matching user in Zulip
        # We search a user's full name, short name,
        # and beginning of email address
        user = UserProfile.objects.filter(
            Q(full_name__iexact=harbor_username) |
            Q(short_name__iexact=harbor_username) |
            Q(email__istartswith=harbor_username),
            is_active=True,
            realm=realm).order_by("id")[0]
        return user
    except IndexError:
        return None


def get_event_type(payload: Dict[str, Any]) -> Optional[str]:
    event = payload["type"]
    return event


def get_event_topic(payload: Dict[str, Any]) -> Optional[str]:
    topic = payload["event_data"]["repository"]["repo_full_name"]
    return topic


def handle_push_image_event(payload: Dict[str, Any], user_profile: UserProfile, operator_username: str) -> str:
    image_name = payload["event_data"]["repository"]["repo_full_name"]
    image_tag = payload["event_data"]["resources"][0]["tag"]

    return u"{author} pushed image `{image_name}:{image_tag}`".format(
        author=operator_username,
        image_name=image_name,
        image_tag=image_tag
    )


VULNERABILITY_SEVERITY_NAME_MAP = {
    1: "None",
    2: "Unknown",
    3: "Low",
    4: "Medium",
    5: "High",
}

SCANNING_COMPLETED_TEMPLATE = """
Image scan completed for `{image_name}:{image_tag}`. Vulnerabilities by severity:

{scan_results}
""".strip()


def handle_scanning_completed_event(payload: Dict[str, Any], user_profile: UserProfile, operator_username: str) -> str:
    scan_results = u""
    scan_summaries = payload["event_data"]["resources"][0]["scan_overview"]["components"]["summary"]
    summaries_sorted = sorted(scan_summaries, key=lambda x: x["severity"], reverse=True)
    for scan_summary in summaries_sorted:
        scan_results += u"* {}: {}\n".format(
            VULNERABILITY_SEVERITY_NAME_MAP[scan_summary["severity"]], scan_summary["count"])

    return SCANNING_COMPLETED_TEMPLATE.format(
        image_name=payload["event_data"]["repository"]["repo_full_name"],
        image_tag=payload["event_data"]["resources"][0]["tag"],
        scan_results=scan_results
    )


EVENT_FUNCTION_MAPPER = {
    "pushImage": handle_push_image_event,
    "scanningCompleted": handle_scanning_completed_event,
}


def get_event_handler(event: Optional[str]) -> Optional[Callable[..., str]]:
    if event is None:
        return None

    return EVENT_FUNCTION_MAPPER.get(event)


@api_key_only_webhook_view("Harbor")
@has_request_variables
def api_harbor_webhook(request: HttpRequest, user_profile: UserProfile,
                       payload: Dict[str, Any] = REQ(argument_type='body')) -> HttpResponse:

    operator_username = u"**{}**".format(payload["operator"])

    if operator_username != "auto":
        operator_profile = guess_zulip_user_from_harbor(
            operator_username, user_profile.realm)

    if operator_profile:
        operator_username = u"@**{}**".format(operator_profile.full_name)

    event = get_event_type(payload)
    topic = get_event_topic(payload)

    if event in IGNORED_EVENTS:
        return json_success()

    content_func = get_event_handler(event)

    if content_func is None:
        raise UnexpectedWebhookEventType('Harbor', event)

    content = content_func(payload, user_profile,
                           operator_username)  # type: str

    check_send_webhook_message(request, user_profile,
                               topic, content,
                               unquote_url_parameters=True)
    return json_success()
