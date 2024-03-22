from typing import List

from django.db import connection
from psycopg2.extras import execute_values
from psycopg2.sql import SQL

from zerver.models import UserMessage


class UserMessageLite:
    """
    The Django ORM is too slow for bulk operations.  This class
    is optimized for the simple use case of inserting a bunch of
    rows into zerver_usermessage.
    """

    def __init__(self, user_profile_id: int, message_id: int, flags: int) -> None:
        self.user_profile_id = user_profile_id
        self.message_id = message_id
        self.flags = flags

    def flags_list(self) -> List[str]:
        return UserMessage.flags_list_for_flags(self.flags)


def bulk_insert_ums(ums: List[UserMessageLite]) -> None:
    """
    Doing bulk inserts this way is much faster than using Django,
    since we don't have any ORM overhead.  Profiling with 1000
    users shows a speedup of 0.436 -> 0.027 seconds, so we're
    talking about a 15x speedup.
    """
    if not ums:
        return

    vals = [(um.user_profile_id, um.message_id, um.flags) for um in ums]
    query = SQL(
        """
        INSERT into
            zerver_usermessage (user_profile_id, message_id, flags)
        VALUES %s
        ON CONFLICT DO NOTHING
    """
    )

    with connection.cursor() as cursor:
        execute_values(cursor.cursor, query, vals)


def bulk_insert_all_ums(user_ids: List[int], message_ids: List[int], flags: int) -> None:
    if not user_ids or not message_ids:
        return

    query = SQL(
        """
        INSERT INTO zerver_usermessage (user_profile_id, message_id, flags)
        SELECT user_profile_id, message_id, %s AS flags
          FROM UNNEST(%s) user_profile_id
          CROSS JOIN UNNEST(%s) message_id
        ON CONFLICT DO NOTHING
        """
    )

    with connection.cursor() as cursor:
        cursor.execute(query, [flags, user_ids, message_ids])
