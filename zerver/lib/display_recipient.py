from typing import Dict, List, Optional, Set, Tuple, TypedDict

from django_stubs_ext import ValuesQuerySet

from zerver.lib.cache import (
    bulk_cached_fetch,
    cache_with_key,
    display_recipient_bulk_get_users_by_id_cache_key,
    display_recipient_cache_key,
    transformed_bulk_cached_fetch,
)
from zerver.lib.types import DisplayRecipientT, UserDisplayRecipient
from zerver.models import Recipient, Stream, UserProfile, bulk_get_huddle_user_ids

display_recipient_fields = [
    "id",
    "email",
    "full_name",
    "is_mirror_dummy",
]


class TinyStreamResult(TypedDict):
    recipient_id: int
    name: str


def get_display_recipient_cache_key(
    recipient_id: int, recipient_type: int, recipient_type_id: Optional[int]
) -> str:
    return display_recipient_cache_key(recipient_id)


@cache_with_key(get_display_recipient_cache_key, timeout=3600 * 24 * 7)
def get_display_recipient_remote_cache(
    recipient_id: int, recipient_type: int, recipient_type_id: Optional[int]
) -> DisplayRecipientT:
    """
    returns: an appropriate object describing the recipient.  For a
    stream this will be the stream name as a string.  For a huddle or
    personal, it will be an array of dicts about each recipient.
    """
    if recipient_type == Recipient.STREAM:
        assert recipient_type_id is not None
        stream = Stream.objects.values("name").get(id=recipient_type_id)
        return stream["name"]

    # The main priority for ordering here is being deterministic.
    # Right now, we order by ID, which matches the ordering of user
    # names in the left sidebar.
    user_profile_list = (
        UserProfile.objects.filter(
            subscription__recipient_id=recipient_id,
        )
        .order_by("id")
        .values(*display_recipient_fields)
    )
    return list(user_profile_list)


def user_dict_id_fetcher(user_dict: UserDisplayRecipient) -> int:
    return user_dict["id"]


def bulk_get_user_display_recipient(uids: List[int]) -> Dict[int, UserDisplayRecipient]:
    return bulk_cached_fetch(
        # Use a separate cache key to protect us from conflicts with
        # the get_user_profile_by_id cache.
        # (Since we fetch only several fields here)
        cache_key_function=display_recipient_bulk_get_users_by_id_cache_key,
        query_function=lambda ids: list(
            UserProfile.objects.filter(id__in=ids).values(*display_recipient_fields)
        ),
        object_ids=uids,
        id_fetcher=user_dict_id_fetcher,
    )


def bulk_fetch_stream_names(
    recipient_tuples: Set[Tuple[int, int, int]],
) -> Dict[int, str]:
    """
    Takes set of tuples of the form (recipient_id, recipient_type, recipient_type_id)
    Returns dict mapping recipient_id to corresponding display_recipient
    """

    if len(recipient_tuples) == 0:
        return {}

    recipient_id_to_stream_id = {tup[0]: tup[2] for tup in recipient_tuples}
    recipient_ids = [tup[0] for tup in recipient_tuples]

    def get_tiny_stream_rows(
        recipient_ids: List[int],
    ) -> ValuesQuerySet[Stream, TinyStreamResult]:
        stream_ids = [recipient_id_to_stream_id[recipient_id] for recipient_id in recipient_ids]
        return Stream.objects.filter(id__in=stream_ids).values("recipient_id", "name")

    def get_recipient_id(row: TinyStreamResult) -> int:
        return row["recipient_id"]

    def get_name(row: TinyStreamResult) -> str:
        return row["name"]

    # ItemT = TinyStreamResult, CacheItemT = str (name), ObjKT = int (recipient_id)
    stream_display_recipients: Dict[int, str] = transformed_bulk_cached_fetch(
        cache_key_function=display_recipient_cache_key,
        query_function=get_tiny_stream_rows,
        object_ids=recipient_ids,
        id_fetcher=get_recipient_id,
        cache_transformer=get_name,
    )

    return stream_display_recipients


def bulk_fetch_user_display_recipients(
    recipient_tuples: Set[Tuple[int, int, int]],
) -> Dict[int, List[UserDisplayRecipient]]:
    """
    Takes set of tuples of the form (recipient_id, recipient_type, recipient_type_id)
    Returns dict mapping recipient_id to corresponding display_recipient
    """

    if len(recipient_tuples) == 0:
        return {}

    recipient_id_to_type = {recipient[0]: recipient[1] for recipient in recipient_tuples}

    recipient_id_to_type_id = {recipient[0]: recipient[2] for recipient in recipient_tuples}

    recipient_ids = [recipient[0] for recipient in recipient_tuples]

    # Now we have to create display_recipients for personal and huddle messages.
    # We do this via generic_bulk_cached_fetch, supplying appropriate functions to it.

    def personal_and_huddle_query_function(
        recipient_ids: List[int],
    ) -> List[Tuple[int, List[UserDisplayRecipient]]]:
        """
        Return a list of tuples of the form (recipient_id, [list of UserProfiles])
        where [list of UserProfiles] has users corresponding to the recipient,
        so the receiving userin Recipient.PERSONAL case,
        or in Personal.HUDDLE case - users in the huddle.
        This is a pretty hacky return value, but it needs to be in this form,
        for this function to work as the query_function in generic_bulk_cached_fetch.
        """

        personal_recipient_ids = [
            recipient_id
            for recipient_id in recipient_ids
            if recipient_id_to_type[recipient_id] == Recipient.PERSONAL
        ]
        huddle_recipient_ids = [
            recipient_id
            for recipient_id in recipient_ids
            if recipient_id_to_type[recipient_id] == Recipient.HUDDLE
        ]

        huddle_user_id_dict = bulk_get_huddle_user_ids(huddle_recipient_ids)

        # Find all user ids whose UserProfiles we will need to fetch:
        user_ids_to_fetch: Set[int] = set()

        for recipient_id in personal_recipient_ids:
            user_id = recipient_id_to_type_id[recipient_id]
            user_ids_to_fetch.add(user_id)

        for recipient_id in huddle_recipient_ids:
            user_ids_to_fetch |= set(huddle_user_id_dict[recipient_id])

        # Fetch the needed user dictionaries.
        user_display_recipients = bulk_get_user_display_recipient(list(user_ids_to_fetch))

        result: List[Tuple[int, List[UserDisplayRecipient]]] = []

        for recipient_id in personal_recipient_ids:
            user_id = recipient_id_to_type_id[recipient_id]
            display_recipients = [user_display_recipients[user_id]]
            result.append((recipient_id, display_recipients))

        for recipient_id in huddle_recipient_ids:
            user_ids = huddle_user_id_dict[recipient_id]
            display_recipients = [user_display_recipients[user_id] for user_id in user_ids]
            result.append((recipient_id, display_recipients))

        return result

    def personal_and_huddle_cache_transformer(
        db_object: Tuple[int, List[UserDisplayRecipient]],
    ) -> List[UserDisplayRecipient]:
        """
        Takes an element of the list returned by the query_function, maps it to the final
        display_recipient list.
        """
        user_profile_list = db_object[1]
        display_recipient = user_profile_list

        return display_recipient

    def personal_and_huddle_id_fetcher(db_object: Tuple[int, List[UserDisplayRecipient]]) -> int:
        # db_object is a tuple, with recipient_id in the first position
        return db_object[0]

    # ItemT = Tuple[int, List[UserDisplayRecipient]] (recipient_id, list of corresponding users)
    # CacheItemT = List[UserDisplayRecipient] (display_recipient list)
    # ObjKT = int (recipient_id)
    personal_and_huddle_display_recipients: Dict[
        int, List[UserDisplayRecipient]
    ] = transformed_bulk_cached_fetch(
        cache_key_function=display_recipient_cache_key,
        query_function=personal_and_huddle_query_function,
        object_ids=recipient_ids,
        id_fetcher=personal_and_huddle_id_fetcher,
        cache_transformer=personal_and_huddle_cache_transformer,
    )

    return personal_and_huddle_display_recipients


def bulk_fetch_display_recipients(
    recipient_tuples: Set[Tuple[int, int, int]],
) -> Dict[int, DisplayRecipientT]:
    """
    Takes set of tuples of the form (recipient_id, recipient_type, recipient_type_id)
    Returns dict mapping recipient_id to corresponding display_recipient
    """

    stream_recipients = {
        recipient for recipient in recipient_tuples if recipient[1] == Recipient.STREAM
    }
    personal_and_huddle_recipients = recipient_tuples - stream_recipients

    stream_display_recipients = bulk_fetch_stream_names(stream_recipients)
    personal_and_huddle_display_recipients = bulk_fetch_user_display_recipients(
        personal_and_huddle_recipients
    )

    # Glue the dicts together and return:
    return {**stream_display_recipients, **personal_and_huddle_display_recipients}
