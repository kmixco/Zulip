import logging
from typing import Optional

from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from pydantic import Json

from corporate.lib.remote_billing_util import (
    RemoteBillingIdentityDict,
    get_identity_dict_from_session,
)
from zerver.decorator import self_hosting_management_endpoint
from zerver.lib.exceptions import JsonableError, MissingRemoteRealmError
from zerver.lib.remote_server import RealmDataForAnalytics, UserDataForRemoteBilling
from zerver.lib.response import json_success
from zerver.lib.typed_endpoint import PathOnly, typed_endpoint
from zilencer.models import RemoteRealm, RemoteZulipServer

billing_logger = logging.getLogger("corporate.stripe")


@csrf_exempt
@typed_endpoint
def remote_server_billing_entry(
    request: HttpRequest,
    remote_server: RemoteZulipServer,
    *,
    user: Json[UserDataForRemoteBilling],
    realm: Json[RealmDataForAnalytics],
) -> HttpResponse:
    if not settings.DEVELOPMENT:
        return render(request, "404.html", status=404)

    try:
        remote_realm = RemoteRealm.objects.get(uuid=realm.uuid, server=remote_server)
    except RemoteRealm.DoesNotExist:
        # This error will prod the remote server to submit its realm info, which
        # should lead to the creation of this missing RemoteRealm registration.
        raise MissingRemoteRealmError

    identity_dict = RemoteBillingIdentityDict(
        user_email=user.email,
        user_uuid=str(user.uuid),
        user_full_name=user.full_name,
        remote_server_uuid=str(remote_server.uuid),
        remote_realm_uuid=str(remote_realm.uuid),
    )

    signed_identity_dict = signing.dumps(identity_dict)

    billing_access_url = (
        f"{settings.EXTERNAL_URI_SCHEME}{settings.SELF_HOSTING_MANAGEMENT_SUBDOMAIN}.{settings.EXTERNAL_HOST}"
        + reverse(remote_server_billing_finalize_login, args=[signed_identity_dict])
    )
    return json_success(request, data={"billing_access_url": billing_access_url})


@self_hosting_management_endpoint
def remote_server_billing_finalize_login(
    request: HttpRequest, signed_billing_access_token: str
) -> HttpResponse:
    try:
        identity_dict: RemoteBillingIdentityDict = signing.loads(
            signed_billing_access_token, max_age=settings.SIGNED_ACCESS_TOKEN_VALIDITY_IN_SECONDS
        )
    except signing.SignatureExpired:
        raise JsonableError(_("Billing access token expired."))
    except signing.BadSignature:
        raise JsonableError(_("Invalid billing access token."))

    remote_realm_uuid = identity_dict["remote_realm_uuid"]

    request.session["remote_billing_identities"] = {}
    request.session["remote_billing_identities"][remote_realm_uuid] = identity_dict

    # TODO: Figure out redirects based on whether the realm/server already has a plan
    # and should be taken to /billing or doesn't have and should be taken to /plans.
    # For now we're only implemented the case where we have the RemoteRealm, and we take
    # to /plans.

    return HttpResponseRedirect(reverse("remote_billing_plans_realm", args=(remote_realm_uuid,)))


def render_tmp_remote_billing_page(
    request: HttpRequest, realm_uuid: Optional[str], server_uuid: Optional[str]
) -> HttpResponse:
    identity_dict = get_identity_dict_from_session(
        request, realm_uuid=realm_uuid, server_uuid=server_uuid
    )

    if identity_dict is None:
        raise JsonableError(_("User not authenticated"))

    user_email = identity_dict["user_email"]
    user_full_name = identity_dict["user_full_name"]
    remote_server_uuid = identity_dict["remote_server_uuid"]
    remote_realm_uuid = identity_dict["remote_realm_uuid"]

    try:
        remote_server = RemoteZulipServer.objects.get(uuid=remote_server_uuid)
    except RemoteZulipServer.DoesNotExist:
        raise JsonableError(_("Invalid remote server."))

    try:
        # Checking for the (uuid, server) is sufficient to be secure here, since the server
        # is authenticated. the uuid_owner_secret is not needed here, it'll be used for
        # for validating transfers of a realm to a different RemoteZulipServer (in the
        # export-import process).
        remote_realm = RemoteRealm.objects.get(uuid=remote_realm_uuid, server=remote_server)
    except RemoteRealm.DoesNotExist:
        raise AssertionError(
            "The remote realm is missing despite being in the RemoteBillingIdentityDict"
        )

    remote_server_and_realm_info = {
        "remote_server_uuid": remote_server_uuid,
        "remote_server_hostname": remote_server.hostname,
        "remote_server_contact_email": remote_server.contact_email,
        "remote_server_plan_type": remote_server.plan_type,
        "remote_realm_uuid": remote_realm_uuid,
        "remote_realm_host": remote_realm.host,
    }

    return render(
        request,
        "corporate/remote_billing.html",
        context={
            "user_email": user_email,
            "user_full_name": user_full_name,
            "remote_server_and_realm_info": remote_server_and_realm_info,
        },
    )


def remote_billing_plans_common(
    request: HttpRequest, realm_uuid: Optional[str], server_uuid: Optional[str]
) -> HttpResponse:
    """
    Once implemented, this function, shared between remote_billing_plans_realm
    and remote_billing_plans_server, will return a Plans page, adjusted depending
    on whether the /realm/... or /server/... endpoint is being used
    """

    return render_tmp_remote_billing_page(request, realm_uuid=realm_uuid, server_uuid=server_uuid)


@self_hosting_management_endpoint
@typed_endpoint
def remote_billing_plans_realm(request: HttpRequest, *, realm_uuid: PathOnly[str]) -> HttpResponse:
    return remote_billing_plans_common(request, realm_uuid=realm_uuid, server_uuid=None)


@self_hosting_management_endpoint
@typed_endpoint
def remote_billing_plans_server(
    request: HttpRequest, *, server_uuid: PathOnly[str]
) -> HttpResponse:
    return remote_billing_plans_common(request, server_uuid=server_uuid, realm_uuid=None)


def remote_billing_page_common(
    request: HttpRequest, realm_uuid: Optional[str], server_uuid: Optional[str]
) -> HttpResponse:
    """
    Once implemented, this function, shared between remote_billing_page_realm
    and remote_billing_page_server, will return a Billing page, adjusted depending
    on whether the /realm/... or /server/... endpoint is being used
    """

    return render_tmp_remote_billing_page(request, realm_uuid=realm_uuid, server_uuid=server_uuid)


@self_hosting_management_endpoint
@typed_endpoint
def remote_billing_page_server(request: HttpRequest, *, server_uuid: PathOnly[str]) -> HttpResponse:
    return remote_billing_page_common(request, server_uuid=server_uuid, realm_uuid=None)


@self_hosting_management_endpoint
@typed_endpoint
def remote_billing_page_realm(request: HttpRequest, *, realm_uuid: PathOnly[str]) -> HttpResponse:
    return remote_billing_page_common(request, realm_uuid=realm_uuid, server_uuid=None)
