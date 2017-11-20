
import os
import re
import ujson

from django.conf import settings
from django.utils.translation import ugettext as _
from typing import Optional, Text, Tuple

from zerver.lib.request import JsonableError
from zerver.lib.upload import upload_backend
from zerver.models import Reaction, Realm, RealmEmoji, UserProfile

NAME_TO_CODEPOINT_PATH = os.path.join(settings.STATIC_ROOT, "generated", "emoji", "name_to_codepoint.json")
CODEPOINT_TO_NAME_PATH = os.path.join(settings.STATIC_ROOT, "generated", "emoji", "codepoint_to_name.json")

with open(NAME_TO_CODEPOINT_PATH) as fp:
    name_to_codepoint = ujson.load(fp)

with open(CODEPOINT_TO_NAME_PATH) as fp:
    codepoint_to_name = ujson.load(fp)

def emoji_name_to_emoji_code(realm, emoji_name):
    # type: (Realm, Text) -> Tuple[Text, Text]
    realm_emojis = realm.get_emoji()
    if emoji_name in realm_emojis and not realm_emojis[emoji_name]['deactivated']:
        return emoji_name, Reaction.REALM_EMOJI
    if emoji_name == 'zulip':
        return emoji_name, Reaction.ZULIP_EXTRA_EMOJI
    if emoji_name in name_to_codepoint:
        return name_to_codepoint[emoji_name], Reaction.UNICODE_EMOJI
    raise JsonableError(_("Emoji '%s' does not exist" % (emoji_name,)))

def check_valid_emoji(realm, emoji_name):
    # type: (Realm, Text) -> None
    emoji_name_to_emoji_code(realm, emoji_name)

def check_emoji_name_consistency(emoji_name: str, emoji_code: str, emoji_type: str) -> None:
    # Given a realm, emoji code and emoji type, checks whether the
    # passed emoji name is a valid name for that emoji. It is assumed
    # here that the emoji code has been checked for validity before
    # calling this function.
    if emoji_type == "realm_emoji":
        if emoji_code == emoji_name:
            return
    elif emoji_type == "zulip_extra_emoji":
        if emoji_name in ["zulip"]:
            return
    elif emoji_type == "unicode_emoji":
        if name_to_codepoint.get(emoji_name) == emoji_code:
            return
    else:
        raise AssertionError("Emoji type should have been checked previously.")

    raise JsonableError(_("Invalid emoji name."))

def check_emoji_code_consistency(realm: Realm, emoji_code: str, emoji_type: str) -> None:
    # For a given realm and emoji type, checks whether an emoji
    # code is valid for new reactions, or not.
    if emoji_type == "realm_emoji":
        realm_emojis = realm.get_emoji()
        if emoji_code not in realm_emojis:
            raise JsonableError(_("No such realm emoji found."))
        if realm_emojis[emoji_code]["deactivated"]:
            raise JsonableError(_("This realm emoji has been deactivated."))
    elif emoji_type == "zulip_extra_emoji":
        if emoji_code not in ["zulip"]:
            raise JsonableError(_("No such extra emoji found."))
    elif emoji_type == "unicode_emoji":
        if emoji_code not in codepoint_to_name:
            raise JsonableError(_("No unicode emoji with this emoji code found."))
    else:
        # The above are the only valid emoji types
        raise JsonableError(_("Invalid emoji type."))

def check_emoji_admin(user_profile, emoji_name=None):
    # type: (UserProfile, Optional[Text]) -> None
    """Raises an exception if the user cannot administer the target realm
    emoji name in their organization."""

    # Realm administrators can always administer emoji
    if user_profile.is_realm_admin:
        return
    if user_profile.realm.add_emoji_by_admins_only:
        raise JsonableError(_("Must be a realm administrator"))

    # Otherwise, normal users can add emoji
    if emoji_name is None:
        return

    # Additionally, normal users can remove emoji they themselves added
    emoji = RealmEmoji.objects.filter(name=emoji_name).first()
    current_user_is_author = (emoji is not None and
                              emoji.author is not None and
                              emoji.author.id == user_profile.id)
    if not user_profile.is_realm_admin and not current_user_is_author:
        raise JsonableError(_("Must be a realm administrator or emoji author"))

def check_valid_emoji_name(emoji_name):
    # type: (Text) -> None
    if re.match('^[0-9a-z.\-_]+(?<![.\-_])$', emoji_name):
        return
    raise JsonableError(_("Invalid characters in emoji name"))

def get_emoji_url(emoji_file_name, realm_id):
    # type: (Text, int) -> Text
    return upload_backend.get_emoji_url(emoji_file_name, realm_id)


def get_emoji_file_name(emoji_file_name, emoji_name):
    # type: (Text, Text) -> Text
    _, image_ext = os.path.splitext(emoji_file_name)
    return ''.join((emoji_name, image_ext))
