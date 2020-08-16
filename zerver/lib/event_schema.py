"""
This is new module that we intend to GROW from test_events.py.

It will contain schemas (aka validators) for Zulip events.

Right now it's only intended to be used by test code.
"""
from typing import Dict, List, Sequence, Tuple, Union

from zerver.lib.data_types import (
    DictType,
    EnumType,
    Equals,
    ListType,
    NumberType,
    OptionalType,
    StringDictType,
    TupleType,
    UnionType,
    UrlType,
    check_data,
    event_dict_type,
    make_checker,
)
from zerver.lib.topic import ORIG_TOPIC, TOPIC_LINKS, TOPIC_NAME
from zerver.lib.validator import Validator, check_dict_only, check_int
from zerver.models import Realm, Stream, Subscription, UserProfile

# These fields are used for "stream" events, and are included in the
# larger "subscription" events that also contain personal settings.
basic_stream_fields = [
    ("description", str),
    ("first_message_id", OptionalType(int)),
    ("history_public_to_subscribers", bool),
    ("invite_only", bool),
    ("is_announcement_only", bool),
    ("is_web_public", bool),
    ("message_retention_days", OptionalType(int)),
    ("name", str),
    ("rendered_description", str),
    ("stream_id", int),
    ("stream_post_policy", int),
    ("date_created", int),
]

subscription_fields: Sequence[Tuple[str, object]] = [
    *basic_stream_fields,
    ("audible_notifications", OptionalType(bool)),
    ("color", str),
    ("desktop_notifications", OptionalType(bool)),
    ("email_address", str),
    ("email_notifications", OptionalType(bool)),
    ("in_home_view", bool),
    ("is_muted", bool),
    ("pin_to_top", bool),
    ("push_notifications", OptionalType(bool)),
    ("role", EnumType(Subscription.ROLE_TYPES)),
    ("stream_weekly_traffic", OptionalType(int)),
    ("wildcard_mentions_notify", OptionalType(bool)),
]


def check_events_dict(
    required_keys: Sequence[Tuple[str, Validator[object]]],
    optional_keys: Sequence[Tuple[str, Validator[object]]] = [],
) -> Validator[Dict[str, object]]:
    """
    This is just a tiny wrapper on check_dict_only, but it provides
    some minor benefits:

        - mark clearly that the schema is for a Zulip event
        - make sure there's a type field
        - add id field automatically
        - sanity check that we have no duplicate keys (we
          should just make check_dict_only do that, eventually)

    """
    rkeys = [key[0] for key in required_keys]
    okeys = [key[0] for key in optional_keys]
    keys = rkeys + okeys
    assert len(keys) == len(set(keys))
    assert "type" in rkeys
    assert "id" not in keys
    return check_dict_only(
        required_keys=[*required_keys, ("id", check_int)],
        optional_keys=optional_keys,
    )


equals_add_or_remove = UnionType(
    [
        # force vertical
        Equals("add"),
        Equals("remove"),
    ]
)

value_type = UnionType(
    [
        # force vertical formatting
        bool,
        int,
        str,
    ]
)

optional_value_type = UnionType(
    [
        # force vertical formatting
        bool,
        int,
        str,
        Equals(None),
    ]
)

alert_words_event = event_dict_type(
    required_keys=[
        # force vertical formatting
        ("type", Equals("alert_words")),
        ("alert_words", ListType(str)),
    ]
)
check_alert_words = make_checker(alert_words_event)

attachment_message_type = DictType(
    required_keys=[
        # force vertical
        ("id", int),
        ("date_sent", int),
    ]
)

attachment_type = DictType(
    required_keys=[
        ("id", int),
        ("name", str),
        ("size", int),
        ("path_id", str),
        ("create_time", int),
        ("messages", ListType(attachment_message_type)),
    ]
)

attachment_add_event = event_dict_type(
    required_keys=[
        ("type", Equals("attachment")),
        ("op", Equals("add")),
        ("attachment", attachment_type),
        ("upload_space_used", int),
    ]
)
check_attachment_add = make_checker(attachment_add_event)

attachment_remove_event = event_dict_type(
    required_keys=[
        ("type", Equals("attachment")),
        ("op", Equals("remove")),
        ("attachment", DictType([("id", int)])),
        ("upload_space_used", int),
    ]
)
check_attachment_remove = make_checker(attachment_remove_event)

attachment_update_event = event_dict_type(
    required_keys=[
        ("type", Equals("attachment")),
        ("op", Equals("update")),
        ("attachment", attachment_type),
        ("upload_space_used", int),
    ]
)
check_attachment_update = make_checker(attachment_update_event)

custom_profile_field_type = DictType(
    required_keys=[
        ("id", int),
        ("type", int),
        ("name", str),
        ("hint", str),
        ("field_data", str),
        ("order", int),
    ],
)

custom_profile_fields_event = event_dict_type(
    required_keys=[
        ("type", Equals("custom_profile_fields")),
        ("op", Equals("add")),
        ("fields", ListType(custom_profile_field_type)),
    ]
)
check_custom_profile_fields = make_checker(custom_profile_fields_event)

_check_stream_group = DictType(
    required_keys=[
        ("name", str),
        ("id", int),
        ("description", str),
        ("streams", ListType(DictType(basic_stream_fields))),
    ]
)

default_stream_groups_event = event_dict_type(
    required_keys=[
        # force vertical
        ("type", Equals("default_stream_groups")),
        ("default_stream_groups", ListType(_check_stream_group)),
    ]
)
check_default_stream_groups = make_checker(default_stream_groups_event)

default_streams_event = event_dict_type(
    required_keys=[
        ("type", Equals("default_streams")),
        ("default_streams", ListType(DictType(basic_stream_fields))),
    ]
)
check_default_streams = make_checker(default_streams_event)

delete_message_event = event_dict_type(
    required_keys=[
        # force vertical
        ("type", Equals("delete_message")),
        ("message_type", EnumType(["private", "stream"])),
    ],
    optional_keys=[
        ("message_id", int),
        ("message_ids", ListType(int)),
        ("stream_id", int),
        ("topic", str),
        ("recipient_id", int),
        ("sender_id", int),
    ],
)
_check_delete_message = make_checker(delete_message_event)


def check_delete_message(
    var_name: str,
    event: Dict[str, object],
    message_type: str,
    num_message_ids: int,
    is_legacy: bool,
) -> None:
    _check_delete_message(var_name, event)

    keys = {"id", "type", "message_type"}

    assert event["message_type"] == message_type

    if message_type == "stream":
        keys |= {"stream_id", "topic"}
    elif message_type == "private":
        keys |= {"recipient_id", "sender_id"}
    else:
        raise AssertionError("unexpected message_type")

    if is_legacy:
        assert num_message_ids == 1
        keys.add("message_id")
    else:
        assert isinstance(event["message_ids"], list)
        assert num_message_ids == len(event["message_ids"])
        keys.add("message_ids")

    assert set(event.keys()) == keys


_hotspot = DictType(
    required_keys=[
        # force vertical
        ("name", str),
        ("title", str),
        ("description", str),
        ("delay", NumberType()),
    ]
)

hotspots_event = event_dict_type(
    required_keys=[
        # force vertical
        ("type", Equals("hotspots")),
        ("hotspots", ListType(_hotspot),),
    ]
)
check_hotspots = make_checker(hotspots_event)

invites_changed_event = event_dict_type(
    required_keys=[
        # the most boring event...no metadata
        ("type", Equals("invites_changed")),
    ]
)
check_invites_changed = make_checker(invites_changed_event)

muted_topic_type = TupleType(
    [
        # We should use objects, not tuples!
        str,  # stream name
        str,  # topic name
        int,  # timestamp
    ]
)

muted_topics_event = event_dict_type(
    required_keys=[
        ("type", Equals("muted_topics")),
        ("muted_topics", ListType(muted_topic_type)),
    ]
)
check_muted_topics = make_checker(muted_topics_event)

message_fields = [
    ("avatar_url", OptionalType(str)),
    ("client", str),
    ("content", str),
    ("content_type", Equals("text/html")),
    ("display_recipient", str),
    ("id", int),
    ("is_me_message", bool),
    ("reactions", ListType(dict)),
    ("recipient_id", int),
    ("sender_realm_str", str),
    ("sender_email", str),
    ("sender_full_name", str),
    ("sender_id", int),
    ("stream_id", int),
    (TOPIC_NAME, str),
    (TOPIC_LINKS, ListType(str)),
    ("submessages", ListType(dict)),
    ("timestamp", int),
    ("type", str),
]

message_event = event_dict_type(
    required_keys=[
        ("type", Equals("message")),
        ("flags", ListType(str)),
        ("message", DictType(message_fields)),
    ]
)
check_message = make_checker(message_event)

presence_type = DictType(
    required_keys=[
        ("status", EnumType(["active", "idle"])),
        ("timestamp", int),
        ("client", str),
        ("pushable", bool),
    ]
)

presence_event = event_dict_type(
    required_keys=[
        ("type", Equals("presence")),
        ("user_id", int),
        ("server_timestamp", NumberType()),
        ("presence", StringDictType(presence_type)),
    ],
    optional_keys=[
        # force vertical
        ("email", str),
    ],
)
_check_presence = make_checker(presence_event)


def check_presence(
    var_name: str,
    event: Dict[str, object],
    has_email: bool,
    presence_key: str,
    status: str,
) -> None:
    _check_presence(var_name, event)

    assert ("email" in event) == has_email

    assert isinstance(event["presence"], dict)

    # Our tests only have one presence value.
    assert len(event["presence"]) == 1

    assert list(event["presence"].keys())[0] == presence_key

    assert list(event["presence"].values())[0]["status"] == status


# We will eventually just send user_ids.
reaction_user_type = DictType(
    required_keys=[
        # force vertical
        ("email", str),
        ("full_name", str),
        ("user_id", int),
    ]
)

reaction_event = event_dict_type(
    required_keys=[
        ("type", Equals("reaction")),
        ("op", equals_add_or_remove),
        ("message_id", int),
        ("emoji_name", str),
        ("emoji_code", str),
        ("reaction_type", str),
        ("user_id", int),
        ("user", reaction_user_type),
    ]
)
_check_reaction = make_checker(reaction_event)


def check_reaction(var_name: str, event: Dict[str, object], op: str) -> None:
    _check_reaction(var_name, event)
    assert event["op"] == op


bot_services_outgoing_type = DictType(
    required_keys=[
        # force vertical
        ("base_url", UrlType()),
        ("interface", int),
        ("token", str),
    ]
)

config_data_schema = StringDictType(str)

bot_services_embedded_type = DictType(
    required_keys=[
        # force vertical
        ("service_name", str),
        ("config_data", config_data_schema),
    ]
)

# Note that regular bots just get an empty list of services,
# so the sub_validator for ListType won't matter for them.
bot_services_type = ListType(
    UnionType(
        [
            # force vertical
            bot_services_outgoing_type,
            bot_services_embedded_type,
        ]
    ),
)

bot_type = DictType(
    required_keys=[
        ("user_id", int),
        ("api_key", str),
        ("avatar_url", str),
        ("bot_type", int),
        ("default_all_public_streams", bool),
        ("default_events_register_stream", OptionalType(str)),
        ("default_sending_stream", OptionalType(str)),
        ("email", str),
        ("full_name", str),
        ("is_active", bool),
        ("owner_id", int),
        ("services", bot_services_type),
    ]
)

realm_bot_add_event = event_dict_type(
    required_keys=[
        # force vertical
        ("type", Equals("realm_bot")),
        ("op", Equals("add")),
        ("bot", bot_type),
    ]
)
_check_realm_bot_add = make_checker(realm_bot_add_event)


def check_realm_bot_add(var_name: str, event: Dict[str, object],) -> None:
    _check_realm_bot_add(var_name, event)

    assert isinstance(event["bot"], dict)
    bot_type = event["bot"]["bot_type"]

    services_field = f"{var_name}['bot']['services']"
    services = event["bot"]["services"]

    if bot_type == UserProfile.DEFAULT_BOT:
        check_data(Equals([]), services_field, services)
    elif bot_type == UserProfile.OUTGOING_WEBHOOK_BOT:
        check_data(
            ListType(bot_services_outgoing_type, length=1), services_field, services
        )
    elif bot_type == UserProfile.EMBEDDED_BOT:
        check_data(
            ListType(bot_services_embedded_type, length=1), services_field, services
        )
    else:
        raise AssertionError(f"Unknown bot_type: {bot_type}")


bot_type_for_delete = DictType(
    required_keys=[
        # for legacy reasons we have a dict here
        # with only one key
        ("user_id", int),
    ]
)

realm_bot_delete_event = event_dict_type(
    required_keys=[
        ("type", Equals("realm_bot")),
        ("op", Equals("delete")),
        ("bot", bot_type_for_delete),
    ]
)
check_realm_bot_delete = make_checker(realm_bot_delete_event)

bot_type_for_remove = DictType(
    required_keys=[
        # Why does remove have full_name but delete doesn't?
        # Why do we have both a remove and a delete event
        # for bots?  I don't know the answer as I write this.
        ("full_name", str),
        ("user_id", int),
    ]
)

realm_bot_remove_event = event_dict_type(
    required_keys=[
        ("type", Equals("realm_bot")),
        ("op", Equals("remove")),
        ("bot", bot_type_for_remove),
    ]
)
check_realm_bot_remove = make_checker(realm_bot_remove_event)

bot_type_for_update = DictType(
    required_keys=[
        # force vertical
        ("user_id", int),
    ],
    optional_keys=[
        ("api_key", str),
        ("avatar_url", str),
        ("default_all_public_streams", bool),
        ("default_events_register_stream", OptionalType(str)),
        ("default_sending_stream", OptionalType(str)),
        ("full_name", str),
        ("owner_id", int),
        ("services", bot_services_type),
    ],
)

realm_bot_update_event = event_dict_type(
    required_keys=[
        ("type", Equals("realm_bot")),
        ("op", Equals("update")),
        ("bot", bot_type_for_update),
    ]
)
_check_realm_bot_update = make_checker(realm_bot_update_event)


def check_realm_bot_update(
    # Check schema plus the field.
    var_name: str,
    event: Dict[str, object],
    field: str,
) -> None:
    # Check the overall schema first.
    _check_realm_bot_update(var_name, event)

    assert isinstance(event["bot"], dict)
    assert {"user_id", field} == set(event["bot"].keys())


export_type = DictType(
    required_keys=[
        ("id", int),
        ("export_time", NumberType()),
        ("acting_user_id", int),
        ("export_url", OptionalType(str)),
        ("deleted_timestamp", OptionalType(NumberType())),
        ("failed_timestamp", OptionalType(NumberType())),
        ("pending", bool),
    ]
)

realm_export_event = event_dict_type(
    required_keys=[
        # force vertical
        ("type", Equals("realm_export")),
        ("exports", ListType(export_type),),
    ]
)
_check_realm_export = make_checker(realm_export_event)


def check_realm_export(
    var_name: str,
    event: Dict[str, object],
    has_export_url: bool,
    has_deleted_timestamp: bool,
    has_failed_timestamp: bool,
) -> None:
    """
    Check the overall event first, knowing it has some
    optional types.
    """
    _check_realm_export(var_name, event)

    """
    Theoretically we can have multiple exports, but until
    that happens in practice, we assume our tests are
    gonna have one export.
    """
    assert isinstance(event["exports"], list)
    assert len(event["exports"]) == 1
    export = event["exports"][0]

    """
    Now verify which fields have non-None values.
    """
    assert has_export_url == (export["export_url"] is not None)
    assert has_deleted_timestamp == (export["deleted_timestamp"] is not None)
    assert has_failed_timestamp == (export["failed_timestamp"] is not None)


realm_filter_type = TupleType(
    [
        # we should make this an object
        # see realm_filters_for_realm_remote_cache
        str,  # pattern
        str,  # format string
        int,  # id
    ]
)

realm_filters_event = event_dict_type(
    [
        # force vertical
        ("type", Equals("realm_filters")),
        ("realm_filters", ListType(realm_filter_type)),
    ]
)
check_realm_filters = make_checker(realm_filters_event)

plan_type_extra_data_type = DictType(
    required_keys=[
        # force vertical
        ("upload_quota", int),
    ]
)

"""
realm/update events are flexible for values;
we will use a more strict checker to check
types in a context-specific manner
"""
realm_update_event = event_dict_type(
    required_keys=[
        ("type", Equals("realm")),
        ("op", Equals("update")),
        ("property", str),
        ("value", value_type),
    ],
    optional_keys=[
        # force vertical
        ("extra_data", plan_type_extra_data_type),
    ],
)
_check_realm_update = make_checker(realm_update_event)


def check_realm_update(var_name: str, event: Dict[str, object], prop: str,) -> None:
    """
    Realm updates have these two fields:

        property
        value

    We check not only the basic schema, but also that
    the value people actually matches the type from
    Realm.property_types that we have configured
    for the property.
    """
    _check_realm_update(var_name, event)

    assert prop == event["property"]
    value = event["value"]

    if prop == "plan_type":
        assert isinstance(value, int)
        assert "extra_data" in event.keys()
        return

    assert "extra_data" not in event.keys()

    if prop in ["notifications_stream_id", "signup_notifications_stream_id"]:
        assert isinstance(value, int)
        return

    property_type = Realm.property_types[prop]

    if property_type in (bool, int, str):
        assert isinstance(value, property_type)
    elif property_type == (int, type(None)):
        assert isinstance(value, int)
    elif property_type == (str, type(None)):
        assert isinstance(value, str)
    else:
        raise AssertionError(f"Unexpected property type {property_type}")


authentication_dict = DictType(
    required_keys=[
        ("Google", bool),
        ("Dev", bool),
        ("LDAP", bool),
        ("GitHub", bool),
        ("Email", bool),
    ]
)

authentication_data = DictType(
    required_keys=[
        # this single-key dictionary is an annoying
        # consequence of us using property_type of
        # "default" for legacy reasons
        ("authentication_methods", authentication_dict),
    ]
)

icon_data = DictType(
    required_keys=[
        # force vertical
        ("icon_url", str),
        ("icon_source", str),
    ]
)

logo_data = DictType(
    required_keys=[
        # force vertical
        ("logo_url", str),
        ("logo_source", str),
    ]
)

message_edit_data = DictType(
    required_keys=[
        ("allow_message_editing", bool),
        ("message_content_edit_limit_seconds", int),
        ("allow_community_topic_editing", bool),
    ]
)

night_logo_data = DictType(
    required_keys=[
        # force vertical
        ("night_logo_url", str),
        ("night_logo_source", str),
    ]
)

update_dict_data = UnionType(
    [
        # force vertical
        authentication_data,
        icon_data,
        logo_data,
        message_edit_data,
        night_logo_data,
    ]
)

realm_update_dict_event = event_dict_type(
    required_keys=[
        ("type", Equals("realm")),
        ("op", Equals("update_dict")),
        ("property", EnumType(["default", "icon", "logo", "night_logo"])),
        ("data", update_dict_data),
    ]
)
_check_realm_update_dict = make_checker(realm_update_dict_event)


def check_realm_update_dict(
    # handle union types
    var_name: str,
    event: Dict[str, object],
) -> None:
    _check_realm_update_dict(var_name, event)

    if event["property"] == "default":
        assert isinstance(event["data"], dict)

        if "allow_message_editing" in event["data"]:
            sub_type = message_edit_data
        elif "authentication_methods" in event["data"]:
            sub_type = authentication_data
        else:
            raise AssertionError("unhandled fields in data")

    elif event["property"] == "icon":
        sub_type = icon_data
    elif event["property"] == "logo":
        sub_type = logo_data
    elif event["property"] == "night_logo":
        sub_type = night_logo_data
    else:
        raise AssertionError("unhandled property: {event['property']}")

    check_data(sub_type, f"{var_name}['data']", event["data"])


realm_user_type = DictType(
    required_keys=[
        ("user_id", int),
        ("email", str),
        ("avatar_url", OptionalType(str)),
        ("avatar_version", int),
        ("full_name", str),
        ("is_admin", bool),
        ("is_owner", bool),
        ("is_bot", bool),
        ("is_guest", bool),
        ("is_active", bool),
        ("profile_data", StringDictType(dict)),
        ("timezone", str),
        ("date_joined", str),
    ]
)

realm_user_add_event = event_dict_type(
    required_keys=[
        ("type", Equals("realm_user")),
        ("op", Equals("add")),
        ("person", realm_user_type),
    ]
)
check_realm_user_add = make_checker(realm_user_add_event)

custom_profile_field_type = DictType(
    required_keys=[
        # vertical formatting
        ("id", int),
        ("value", str),
    ],
    optional_keys=[
        # vertical formatting
        ("rendered_value", str),
    ],
)

realm_user_person_types = dict(
    # Note that all flavors of person include user_id.
    avatar_fields=DictType(
        required_keys=[
            ("user_id", int),
            ("avatar_source", str),
            ("avatar_url", OptionalType(str)),
            ("avatar_url_medium", OptionalType(str)),
            ("avatar_version", int),
        ],
    ),
    bot_owner_id=DictType(
        required_keys=[
            # vertical formatting
            ("user_id", int),
            ("bot_owner_id", int),
        ],
    ),
    custom_profile_field=DictType(
        required_keys=[
            # vertical formatting
            ("user_id", int),
            ("custom_profile_field", custom_profile_field_type),
        ],
    ),
    delivery_email=DictType(
        required_keys=[
            # vertical formatting
            ("user_id", int),
            ("delivery_email", str),
        ],
    ),
    full_name=DictType(
        required_keys=[
            # vertical formatting
            ("user_id", int),
            ("full_name", str),
        ],
    ),
    role=DictType(
        required_keys=[
            # vertical formatting
            ("user_id", int),
            ("role", EnumType(UserProfile.ROLE_TYPES)),
        ],
    ),
    timezone=DictType(
        required_keys=[
            # we should probably eliminate email here
            ("user_id", int),
            ("email", str),
            ("timezone", str),
        ],
    ),
)

realm_user_update_event = event_dict_type(
    required_keys=[
        ("type", Equals("realm_user")),
        ("op", Equals("update")),
        ("person", UnionType(list(realm_user_person_types.values()))),
    ],
)
_check_realm_user_update = make_checker(realm_user_update_event)


def check_realm_user_update(
    # person_flavor tells us which extra fields we need
    var_name: str,
    event: Dict[str, object],
    person_flavor: str,
) -> None:
    _check_realm_user_update(var_name, event)

    check_data(
        realm_user_person_types[person_flavor],
        f"{var_name}['person']",
        event["person"],
    )


stream_create_event = event_dict_type(
    required_keys=[
        ("type", Equals("stream")),
        ("op", Equals("create")),
        ("streams", ListType(DictType(basic_stream_fields))),
    ]
)
check_stream_create = make_checker(stream_create_event)

stream_delete_event = event_dict_type(
    required_keys=[
        ("type", Equals("stream")),
        ("op", Equals("delete")),
        ("streams", ListType(DictType(basic_stream_fields))),
    ]
)
check_stream_delete = make_checker(stream_delete_event)

stream_update_event = event_dict_type(
    required_keys=[
        ("type", Equals("stream")),
        ("op", Equals("update")),
        ("property", str),
        ("value", optional_value_type),
        ("name", str),
        ("stream_id", int),
    ],
    optional_keys=[
        ("rendered_description", str),
        ("history_public_to_subscribers", bool),
    ],
)
_check_stream_update = make_checker(stream_update_event)


def check_stream_update(var_name: str, event: Dict[str, object],) -> None:
    _check_stream_update(var_name, event)
    prop = event["property"]
    value = event["value"]

    extra_keys = set(event.keys()) - {
        "id",
        "type",
        "op",
        "property",
        "value",
        "name",
        "stream_id",
    }

    if prop == "description":
        assert extra_keys == {"rendered_description"}
        assert isinstance(value, str)
    elif prop == "email_address":
        assert extra_keys == set()
        assert isinstance(value, str)
    elif prop == "invite_only":
        assert extra_keys == {"history_public_to_subscribers"}
        assert isinstance(value, bool)
    elif prop == "message_retention_days":
        assert extra_keys == set()
        if value is not None:
            assert isinstance(value, int)
    elif prop == "name":
        assert extra_keys == set()
        assert isinstance(value, str)
    elif prop == "stream_post_policy":
        assert extra_keys == set()
        assert value in Stream.STREAM_POST_POLICY_TYPES
    else:
        raise AssertionError(f"Unknown property: {prop}")


submessage_event = event_dict_type(
    required_keys=[
        ("type", Equals("submessage")),
        ("message_id", int),
        ("submessage_id", int),
        ("sender_id", int),
        ("msg_type", str),
        ("content", str),
    ]
)
check_submessage = make_checker(submessage_event)

single_subscription_type = DictType(
    required_keys=subscription_fields,
    optional_keys=[
        # force vertical
        ("subscribers", ListType(int)),
    ],
)

subscription_add_event = event_dict_type(
    required_keys=[
        ("type", Equals("subscription")),
        ("op", Equals("add")),
        ("subscriptions", ListType(single_subscription_type)),
    ],
)
_check_subscription_add = make_checker(subscription_add_event)


def check_subscription_add(
    var_name: str, event: Dict[str, object], include_subscribers: bool,
) -> None:
    _check_subscription_add(var_name, event)

    assert isinstance(event["subscriptions"], list)
    for sub in event["subscriptions"]:
        if include_subscribers:
            assert "subscribers" in sub.keys()
        else:
            assert "subscribers" not in sub.keys()


subscription_peer_add_event = event_dict_type(
    required_keys=[
        ("type", Equals("subscription")),
        ("op", Equals("peer_add")),
        ("user_id", int),
        ("stream_id", int),
    ]
)
check_subscription_peer_add = make_checker(subscription_peer_add_event)

subscription_peer_remove_event = event_dict_type(
    required_keys=[
        ("type", Equals("subscription")),
        ("op", Equals("peer_remove")),
        ("user_id", int),
        ("stream_id", int),
    ]
)
check_subscription_peer_remove = make_checker(subscription_peer_remove_event)

remove_sub_type = DictType(
    required_keys=[
        # We should eventually just return stream_id here.
        ("name", str),
        ("stream_id", int),
    ]
)

subscription_remove_event = event_dict_type(
    required_keys=[
        ("type", Equals("subscription")),
        ("op", Equals("remove")),
        ("subscriptions", ListType(remove_sub_type)),
    ]
)
check_subscription_remove = make_checker(subscription_remove_event)

typing_person_type = DictType(
    required_keys=[
        # we should eventually just send user_id
        ("email", str),
        ("user_id", int),
    ]
)

typing_start_event = event_dict_type(
    required_keys=[
        ("type", Equals("typing")),
        ("op", Equals("start")),
        ("sender", typing_person_type),
        ("recipients", ListType(typing_person_type)),
    ]
)
check_typing_start = make_checker(typing_start_event)

typing_stop_event = event_dict_type(
    required_keys=[
        ("type", Equals("typing")),
        ("op", Equals("stop")),
        ("sender", typing_person_type),
        ("recipients", ListType(typing_person_type)),
    ]
)
check_typing_stop = make_checker(typing_stop_event)

update_display_settings_event = event_dict_type(
    required_keys=[
        ("type", Equals("update_display_settings")),
        ("setting_name", str),
        ("setting", value_type),
        ("user", str),
    ],
    optional_keys=[
        # force vertical
        ("language_name", str),
    ],
)
_check_update_display_settings = make_checker(update_display_settings_event)


def check_update_display_settings(var_name: str, event: Dict[str, object],) -> None:
    """
    Display setting events have a "setting" field that
    is more specifically typed according to the
    UserProfile.property_types dictionary.
    """
    _check_update_display_settings(var_name, event)
    setting_name = event["setting_name"]
    setting = event["setting"]

    assert isinstance(setting_name, str)
    setting_type = UserProfile.property_types[setting_name]
    assert isinstance(setting, setting_type)

    if setting_name == "default_language":
        assert "language_name" in event.keys()
    else:
        assert "language_name" not in event.keys()


update_global_notifications_event = event_dict_type(
    required_keys=[
        ("type", Equals("update_global_notifications")),
        ("notification_name", str),
        ("setting", value_type),
        ("user", str),
    ]
)
_check_update_global_notifications = make_checker(update_global_notifications_event)


def check_update_global_notifications(
    var_name: str, event: Dict[str, object], desired_val: Union[bool, int, str],
) -> None:
    """
    See UserProfile.notification_setting_types for
    more details.
    """
    _check_update_global_notifications(var_name, event)
    setting_name = event["notification_name"]
    setting = event["setting"]
    assert setting == desired_val

    assert isinstance(setting_name, str)
    setting_type = UserProfile.notification_setting_types[setting_name]
    assert isinstance(setting, setting_type)


update_message_required_fields = [
    ("type", Equals("update_message")),
    ("user_id", int),
    ("edit_timestamp", int),
    ("message_id", int),
]

update_message_content_fields: List[Tuple[str, object]] = [
    ("content", str),
    ("is_me_message", bool),
    ("orig_content", str),
    ("orig_rendered_content", str),
    ("prev_rendered_content_version", int),
    ("rendered_content", str),
]

update_message_topic_fields = [
    ("flags", ListType(str)),
    ("message_ids", ListType(int)),
    ("new_stream_id", int),
    (ORIG_TOPIC, str),
    (
        "propagate_mode",
        EnumType(
            [
                # order matches openapi spec
                "change_one",
                "change_later",
                "change_all",
            ]
        ),
    ),
    ("stream_id", int),
    ("stream_name", str),
    (TOPIC_LINKS, ListType(str)),
    (TOPIC_NAME, str),
]

update_message_optional_fields = (
    update_message_content_fields + update_message_topic_fields
)

# The schema here does not include the "embedded"
# variant of update_message; it is for message
# and topic editing.
update_message_event = event_dict_type(
    required_keys=update_message_required_fields,
    optional_keys=update_message_optional_fields,
)
_check_update_message = make_checker(update_message_event)


def check_update_message(
    var_name: str,
    event: Dict[str, object],
    has_content: bool,
    has_topic: bool,
    has_new_stream_id: bool,
) -> None:
    # Always check the basic schema first.
    _check_update_message(var_name, event)

    actual_keys = set(event.keys())
    expected_keys = {"id"}
    expected_keys.update(tup[0] for tup in update_message_required_fields)

    if has_content:
        expected_keys.update(tup[0] for tup in update_message_content_fields)

    if has_topic:
        expected_keys.update(tup[0] for tup in update_message_topic_fields)

    if not has_new_stream_id:
        expected_keys.discard("new_stream_id")

    assert expected_keys == actual_keys


update_message_embedded_event = event_dict_type(
    required_keys=[
        ("type", Equals("update_message")),
        ("flags", ListType(str)),
        ("content", str),
        ("message_id", int),
        ("message_ids", ListType(int)),
        ("rendered_content", str),
    ]
)
check_update_message_embedded = make_checker(update_message_embedded_event)

update_message_flags_event = event_dict_type(
    required_keys=[
        ("type", Equals("update_message_flags")),
        ("op", equals_add_or_remove),
        ("operation", equals_add_or_remove),
        ("flag", str),
        ("messages", ListType(int)),
        ("all", bool),
    ]
)
_check_update_message_flags = make_checker(update_message_flags_event)


def check_update_message_flags(
    var_name: str, event: Dict[str, object], operation: str
) -> None:
    _check_update_message_flags(var_name, event)
    assert event["operation"] == operation and event['op'] == operation


group_type = DictType(
    required_keys=[
        ("id", int),
        ("name", str),
        ("members", ListType(int)),
        ("description", str),
    ]
)

user_group_add_event = event_dict_type(
    required_keys=[
        ("type", Equals("user_group")),
        ("op", Equals("add")),
        ("group", group_type),
    ]
)
check_user_group_add = make_checker(user_group_add_event)

user_group_add_members_event = event_dict_type(
    required_keys=[
        ("type", Equals("user_group")),
        ("op", Equals("add_members")),
        ("group_id", int),
        ("user_ids", ListType(int)),
    ]
)
check_user_group_add_members = make_checker(user_group_add_members_event)

user_group_remove_event = event_dict_type(
    required_keys=[
        ("type", Equals("user_group")),
        ("op", Equals("remove")),
        ("group_id", int),
    ]
)
check_user_group_remove = make_checker(user_group_remove_event)

user_group_remove_members_event = event_dict_type(
    required_keys=[
        ("type", Equals("user_group")),
        ("op", Equals("remove_members")),
        ("group_id", int),
        ("user_ids", ListType(int)),
    ]
)
check_user_group_remove_members = make_checker(user_group_remove_members_event)

user_group_data_type = DictType(
    required_keys=[],
    optional_keys=[
        # force vertical
        ("name", str),
        ("description", str),
    ],
)

user_group_update_event = event_dict_type(
    required_keys=[
        ("type", Equals("user_group")),
        ("op", Equals("update")),
        ("group_id", int),
        ("data", user_group_data_type),
    ]
)
_check_user_group_update = make_checker(user_group_update_event)


def check_user_group_update(
    var_name: str, event: Dict[str, object], field: str
) -> None:
    _check_user_group_update(var_name, event)

    assert isinstance(event["data"], dict)

    assert set(event["data"].keys()) == {field}


user_status_event = event_dict_type(
    required_keys=[
        ("type", Equals("user_status")),
        ("user_id", int),
        ("away", bool),
        ("status_text", str),
    ]
)
check_user_status = make_checker(user_status_event)
