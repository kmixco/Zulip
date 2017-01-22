from __future__ import absolute_import
from collections import defaultdict
from typing import Any
import logging

from django.conf import settings
from django.core.mail import mail_admins

from zerver.models import get_user_profile_by_email
from zerver.lib.actions import internal_send_message
from typing import Dict
import six

def format_subject(subject):
    # type: (str) -> str
    """
    Escape CR and LF characters.
    """
    return subject.replace('\n', '\\n').replace('\r', '\\r')

def user_info_str(report):
    # type: (Dict[str, Any]) -> str
    if report['user_full_name'] and report['user_email']:
        user_info = "%(user_full_name)s (%(user_email)s)" % (report)
    else:
        user_info = "Anonymous user (not logged in)"

    user_info += " on %s deployment"  % (report['deployment'],)
    return user_info

def notify_browser_error(report):
    # type: (Dict[str, Any]) -> None
    report = defaultdict(lambda: None, report)
    if settings.ERROR_BOT:
        zulip_browser_error(report)
    email_browser_error(report)

def email_browser_error(report):
    # type: (Dict[str, Any]) -> None
    subject = "Browser error for %s" % (user_info_str(report))

    body = ("User: %(user_full_name)s <%(user_email)s> on %(deployment)s\n\n"
            "Message:\n%(message)s\n\nStacktrace:\n%(stacktrace)s\n\n"
            "User agent: %(user_agent)s\n"
            "href: %(href)s\n"
            "Server path: %(server_path)s\n"
            "Deployed version: %(version)s\n"
            % (report))

    more_info = report['more_info']
    if more_info is not None:
        body += "\nAdditional information:"
        for (key, value) in six.iteritems(more_info):
            body += "\n  %s: %s" % (key, value)

    body += "\n\nLog:\n%s" % (report['log'],)

    mail_admins(subject, body)

def zulip_browser_error(report):
    # type: (Dict[str, Any]) -> None
    subject = "JS error: %s" % (report['user_email'],)

    user_info = user_info_str(report)

    body = "User: %s\n" % (user_info,)
    body += ("Message: %(message)s\n"
             % (report))

    realm = get_user_profile_by_email(settings.ERROR_BOT).realm
    internal_send_message(realm, settings.ERROR_BOT,
                          "stream", "errors", format_subject(subject), body)

def notify_server_error(report):
    # type: (Dict[str, Any]) -> None
    report = defaultdict(lambda: None, report)
    email_server_error(report)
    if settings.ERROR_BOT:
        zulip_server_error(report)

def zulip_server_error(report):
    # type: (Dict[str, Any]) -> None
    subject = '%(node)s: %(message)s' % (report)
    stack_trace = report['stack_trace'] or "No stack trace available"

    user_info = user_info_str(report)

    request_repr = (
        "Request info:\n~~~~\n"
        "- path: %(path)s\n"
        "- %(method)s: %(data)s\n") % (report)

    for field in ["REMOTE_ADDR", "QUERY_STRING", "SERVER_NAME"]:
        request_repr += "- %s: \"%s\"\n" % (field, report.get(field.lower()))
    request_repr += "~~~~"

    realm = get_user_profile_by_email(settings.ERROR_BOT).realm
    internal_send_message(realm, settings.ERROR_BOT,
                          "stream", "errors", format_subject(subject),
                          "Error generated by %s\n\n~~~~ pytb\n%s\n\n~~~~\n%s" % (
                            user_info, stack_trace, request_repr))

def email_server_error(report):
    # type: (Dict[str, Any]) -> None
    subject = '%(node)s: %(message)s' % (report)

    user_info = user_info_str(report)

    request_repr = (
        "Request info:\n"
        "- path: %(path)s\n"
        "- %(method)s: %(data)s\n") % (report)

    for field in ["REMOTE_ADDR", "QUERY_STRING", "SERVER_NAME"]:
        request_repr += "- %s: \"%s\"\n" % (field, report.get(field.lower()))

    message = "Error generated by %s\n\n%s\n\n%s" % (user_info, report['stack_trace'],
                                                     request_repr)

    mail_admins(format_subject(subject), message, fail_silently=True)
