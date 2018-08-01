import random
from typing import List, Dict, Any
from django.forms.models import model_to_dict

from zerver.models import Realm
from zerver.lib.actions import STREAM_ASSIGNMENT_COLORS as stream_colors

# stubs
ZerverFieldsT = Dict[str, Any]

def build_zerver_realm(realm_id: int, realm_subdomain: str, time: float,
                       other_product: str) -> List[ZerverFieldsT]:
    realm = Realm(id=realm_id, date_created=time,
                  name=realm_subdomain, string_id=realm_subdomain,
                  description=("Organization imported from %s!" % (other_product)))
    auth_methods = [[flag[0], flag[1]] for flag in realm.authentication_methods]
    realm_dict = model_to_dict(realm, exclude='authentication_methods')
    realm_dict['authentication_methods'] = auth_methods
    return[realm_dict]

def build_avatar(zulip_user_id: int, realm_id: int, email: str, avatar_url: str,
                 timestamp: Any, avatar_list: List[ZerverFieldsT]) -> None:
    avatar = dict(
        path=avatar_url,  # Save original avatar url here, which is downloaded later
        realm_id=realm_id,
        content_type=None,
        user_profile_id=zulip_user_id,
        last_modified=timestamp,
        user_profile_email=email,
        s3_path="",
        size="")
    avatar_list.append(avatar)

def build_subscription(recipient_id: int, user_id: int,
                       subscription_id: int) -> ZerverFieldsT:
    subscription = dict(
        recipient=recipient_id,
        color=random.choice(stream_colors),
        audible_notifications=True,
        push_notifications=False,
        email_notifications=False,
        desktop_notifications=True,
        pin_to_top=False,
        in_home_view=True,
        active=True,
        user_profile=user_id,
        id=subscription_id)
    return subscription

def build_recipient(type_id: int, recipient_id: int, type: int) -> ZerverFieldsT:
    recipient = dict(
        type_id=type_id,  # stream id
        id=recipient_id,
        type=type)
    return recipient
