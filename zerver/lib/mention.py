import re
from typing import Match, Optional, Set, Tuple

# Match multi-word string between @** ** or match any one-word
# sequences after @
MENTIONS_RE = re.compile(r"(?<![^\s\'\"\(,:<])@(?P<silent>_?)(\*\*(?P<match>[^\*]+)\*\*)")
USER_GROUP_MENTIONS_RE = re.compile(r"(?<![^\s\'\"\(,:<])@(?P<silent>_?)(\*(?P<match>[^\*]+)\*)")

wildcards = ["all", "everyone", "stream"]


def user_mention_matches_wildcard(mention: str) -> bool:
    return mention in wildcards


def extract_mention_text(m: Match[str]) -> Tuple[Optional[str], bool]:
    text = m.group("match")
    if text in wildcards:
        return None, True
    return text, False


def possible_mentions(content: str) -> Tuple[Set[str], bool]:
    # mention texts can either be names, or an extended name|id syntax.
    texts = set()
    message_has_wildcards = False
    for m in MENTIONS_RE.finditer(content):
        text, is_wildcard = extract_mention_text(m)
        if text:
            texts.add(text)
        if is_wildcard:
            message_has_wildcards = True
    return texts, message_has_wildcards


def possible_user_group_mentions(content: str) -> Set[str]:
    return {m.group("match") for m in USER_GROUP_MENTIONS_RE.finditer(content)}
