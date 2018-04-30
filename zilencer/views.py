
from typing import Any, Dict, Optional, Text, Union, cast

from django.core.validators import validate_email, URLValidator
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext as _, ugettext as err_
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

from zerver.decorator import require_post, zulip_login_required
from zerver.lib.exceptions import JsonableError
from zerver.lib.push_notifications import send_android_push_notification, \
    send_apple_push_notification
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_error, json_success
from zerver.lib.validator import check_int, check_string, check_url, \
    validate_login_email, check_capped_string
from zerver.models import UserProfile, Realm
from zerver.views.push_notifications import validate_token
from zilencer.forms import RemoteServerRegistrationForm
from zilencer.lib.stripe import STRIPE_PUBLISHABLE_KEY, count_stripe_cards, \
    save_stripe_token, StripeError
from zilencer.models import RemotePushDeviceToken, RemoteZulipServer

def validate_entity(entity: Union[UserProfile, RemoteZulipServer]) -> None:
    if not isinstance(entity, RemoteZulipServer):
        raise JsonableError(err_("Must validate with valid Zulip server API key"))

def validate_bouncer_token_request(entity: Union[UserProfile, RemoteZulipServer],
                                   token: bytes, kind: int) -> None:
    if kind not in [RemotePushDeviceToken.APNS, RemotePushDeviceToken.GCM]:
        raise JsonableError(err_("Invalid token type"))
    validate_entity(entity)
    validate_token(token, kind)

def update_or_create_remote_server(zulip_org_id: Text, zulip_org_key: Text, hostname: Text, contact_email: Text) -> bool:
    if len(zulip_org_id) != RemoteZulipServer.UUID_LENGTH:
        raise JsonableError(err_("zulip_org_id must be %s characters. It is currently %s characters."
                                 % (RemoteZulipServer.UUID_LENGTH, len(zulip_org_id))))
    if len(zulip_org_key) != RemoteZulipServer.API_KEY_LENGTH:
        raise JsonableError(err_("zulip_org_key must be %s characters. It is currently %s characters."
                                 % (RemoteZulipServer.API_KEY_LENGTH, len(zulip_org_key))))
    if len(hostname) > RemoteZulipServer.HOSTNAME_MAX_LENGTH:
        raise JsonableError(err_("EXTERNAL_HOST can be at most %s characters. It is currently %s characters."
                                 % (RemoteZulipServer.HOSTNAME_MAX_LENGTH, len(hostname))))
    try:
        url_validator = URLValidator()
        if hostname.startswith('http'):
            url_validator(hostname)
        else:
            url_validator('http://' + hostname)
    except ValidationError:
        raise JsonableError('%s is not a valid URL' % (hostname,))
    try:
        validate_email(email)
    except ValidationError:
        raise JsonableError('%s is not an email address' % (contact_email,))

    try:
        remote_server, created = RemoteZulipServer.objects.update_or_create(
            uuid=zulip_org_id, api_key=zulip_org_key,
            defaults={'hostname': hostname, 'contact_email': contact_email})
    except IntegrityError:
        raise JsonableError(err_("zulip_org_id and zulip_org_key do not match."))
    return created

@require_post
def register_remote_server_via_api(request: HttpRequest) -> HttpResponse:
    created = update_or_create_remote_server(
        request.POST['zulip_org_id'], request.POST['zulip_org_key'],
        request.POST['hostname'], request.POST['contact_email'])
    return json_success({'created': created})

def register_remote_server_via_web(request: HttpRequest) -> HttpResponse:
    success = False
    created = None
    if request.method == 'POST':
        form = RemoteServerRegistrationForm(request.POST)
        if form.is_valid():
            created = update_or_create_remote_server(
                form.cleaned_data['zulip_org_id'], form.cleaned_data['zulip_org_key'],
                form.cleaned_data['hostname'], form.cleaned_data['contact_email'])
            success = True
    else:
        form = RemoteServerRegistrationForm()
    return render(request, 'zilencer/register_remote_server.html',
                  context={'form': form, 'success': success, 'created': created})

@has_request_variables
def register_remote_server_via_web(request: HttpRequest,
                                   zulip_org_id: Text=REQ(validator=check_string),
                                   zulip_org_key: Text=REQ(validator=check_string),
                                   hostname: Text=REQ(validator=check_string),
                                   contact_email: Text=REQ(validator=check_string)) -> HttpResponse:



    created = update_or_create_remote_server(Zulip_org_id, zulip_org_key, hostname, contact_email)
    return json_success({'created': created})


@has_request_variables
def register_remote_push_device(request: HttpRequest, entity: Union[UserProfile, RemoteZulipServer],
                                user_id: int=REQ(), token: bytes=REQ(),
                                token_kind: int=REQ(validator=check_int),
                                ios_app_id: Optional[Text]=None) -> HttpResponse:
    validate_bouncer_token_request(entity, token, token_kind)
    server = cast(RemoteZulipServer, entity)

    # If a user logged out on a device and failed to unregister,
    # we should delete any other user associations for this token
    # & RemoteServer pair
    RemotePushDeviceToken.objects.filter(
        token=token, kind=token_kind, server=server).exclude(user_id=user_id).delete()

    # Save or update
    remote_token, created = RemotePushDeviceToken.objects.update_or_create(
        user_id=user_id,
        server=server,
        kind=token_kind,
        token=token,
        defaults=dict(
            ios_app_id=ios_app_id,
            last_updated=timezone.now()))

    return json_success()

@has_request_variables
def unregister_remote_push_device(request: HttpRequest, entity: Union[UserProfile, RemoteZulipServer],
                                  token: bytes=REQ(),
                                  token_kind: int=REQ(validator=check_int),
                                  ios_app_id: Optional[Text]=None) -> HttpResponse:
    validate_bouncer_token_request(entity, token, token_kind)
    server = cast(RemoteZulipServer, entity)
    deleted = RemotePushDeviceToken.objects.filter(token=token,
                                                   kind=token_kind,
                                                   server=server).delete()
    if deleted[0] == 0:
        return json_error(err_("Token does not exist"))

    return json_success()

@has_request_variables
def remote_server_notify_push(request: HttpRequest, entity: Union[UserProfile, RemoteZulipServer],
                              payload: Dict[str, Any]=REQ(argument_type='body')) -> HttpResponse:
    validate_entity(entity)
    server = cast(RemoteZulipServer, entity)

    user_id = payload['user_id']
    gcm_payload = payload['gcm_payload']
    apns_payload = payload['apns_payload']

    android_devices = list(RemotePushDeviceToken.objects.filter(
        user_id=user_id,
        kind=RemotePushDeviceToken.GCM,
        server=server
    ))

    apple_devices = list(RemotePushDeviceToken.objects.filter(
        user_id=user_id,
        kind=RemotePushDeviceToken.APNS,
        server=server
    ))

    if android_devices:
        send_android_push_notification(android_devices, gcm_payload, remote=True)

    if apple_devices:
        send_apple_push_notification(user_id, apple_devices, apns_payload)

    return json_success()

@zulip_login_required
def add_payment_method(request: HttpRequest) -> HttpResponse:
    user = request.user
    ctx = {
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "email": user.email,
    }  # type: Dict[str, Any]

    if not user.is_realm_admin:
        ctx["error_message"] = (
            _("You should be an administrator of the organization %s to view this page.")
            % (user.realm.name,))
        return render(request, 'zilencer/billing.html', context=ctx)

    try:
        if request.method == "GET":
            ctx["num_cards"] = count_stripe_cards(user.realm)
            return render(request, 'zilencer/billing.html', context=ctx)
        if request.method == "POST":
            token = request.POST.get("stripeToken", "")
            ctx["num_cards"] = save_stripe_token(user, token)
            ctx["payment_method_added"] = True
            return render(request, 'zilencer/billing.html', context=ctx)
    except StripeError as e:
        ctx["error_message"] = e.msg
        return render(request, 'zilencer/billing.html', context=ctx)
