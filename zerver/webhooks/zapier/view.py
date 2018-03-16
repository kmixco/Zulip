from typing import Any, Callable, Dict

from django.http import HttpRequest, HttpResponse
from django.utils.translation import ugettext as _

from zerver.decorator import api_key_only_webhook_view
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_error, json_success
from zerver.lib.webhooks.common import check_send_webhook_message
from zerver.models import UserProfile

@api_key_only_webhook_view('Zapier')
@has_request_variables
def api_zapier_webhook(request: HttpRequest, user_profile: UserProfile,
                       payload: Dict[str, Any]=REQ(argument_type='body')) -> HttpResponse:
    subject = payload.get('subject')
    content = payload.get('content')
    if subject is None:
        return json_error(_("Subject can't be empty"))
    if content is None:
        return json_error(_("Content can't be empty"))
    check_send_webhook_message(request, user_profile, subject, content)
    return json_success()
