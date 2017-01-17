from __future__ import absolute_import
from typing import List, Text

from django.http import HttpRequest, HttpResponse

from zerver.decorator import REQ, has_request_variables
from zerver.lib.actions import (do_add_alert_words, do_remove_alert_words,
                                do_set_alert_words)
from zerver.lib.alert_words import user_alert_words
from zerver.lib.response import json_success
from zerver.lib.validator import check_list, check_string
from zerver.models import UserProfile


def list_alert_words(request, user_profile):
    # type: (HttpRequest, UserProfile) -> HttpResponse
    return json_success({'alert_words': user_alert_words(user_profile)})

@has_request_variables
def set_alert_words(request, user_profile,
                    alert_words=REQ(validator=check_list(check_string), default=[])):
    # type: (HttpRequest, UserProfile, List[Text]) -> HttpResponse
    do_set_alert_words(user_profile, alert_words)
    return json_success()

@has_request_variables
def add_alert_words(request, user_profile,
                    alert_words=REQ(validator=check_list(check_string), default=[])):
    # type: (HttpRequest, UserProfile, List[str]) -> HttpResponse
    do_add_alert_words(user_profile, alert_words)
    return json_success()

@has_request_variables
def remove_alert_words(request, user_profile,
                       alert_words=REQ(validator=check_list(check_string), default=[])):
    # type: (HttpRequest, UserProfile, List[str]) -> HttpResponse
    do_remove_alert_words(user_profile, alert_words)
    return json_success()
