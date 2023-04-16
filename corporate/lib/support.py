from urllib.parse import urlencode, urljoin, urlunsplit

from django.conf import settings
from django.urls import reverse

from zerver.models import Realm, get_realm


def get_support_url(realm: Realm) -> str:
    support_realm_url = get_realm(settings.STAFF_SUBDOMAIN).url
    support_url = urljoin(
        support_realm_url,
        urlunsplit(("", "", reverse("support"), urlencode({"q": realm.string_id}), "")),
    )
    return support_url
