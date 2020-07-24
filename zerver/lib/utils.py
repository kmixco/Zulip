import base64
import hashlib
import heapq
import itertools
import os
import re
import string
from itertools import zip_longest
from time import sleep
from typing import Any, Callable, Iterator, List, Optional, Sequence, Set, Tuple, TypeVar

from django.conf import settings

T = TypeVar('T')

# Runs the callback with slices of all_list of a given batch_size
def run_in_batches(all_list: Sequence[T],
                   batch_size: int,
                   callback: Callable[[Sequence[T]], None],
                   sleep_time: int=0,
                   logger: Optional[Callable[[str], None]]=None) -> None:
    if len(all_list) == 0:
        return

    limit = (len(all_list) // batch_size) + 1
    for i in range(limit):
        start = i*batch_size
        end = (i+1) * batch_size
        if end >= len(all_list):
            end = len(all_list)
        batch = all_list[start:end]

        if logger:
            logger(f"Executing {end-start} in batch {i+1} of {limit}")

        callback(batch)

        if i != limit - 1:
            sleep(sleep_time)

def make_safe_digest(string: str,
                     hash_func: Callable[[bytes], Any]=hashlib.sha1) -> str:
    """
    return a hex digest of `string`.
    """
    # hashlib.sha1, md5, etc. expect bytes, so non-ASCII strings must
    # be encoded.
    return hash_func(string.encode('utf-8')).hexdigest()

def generate_random_token(length: int) -> str:
    return str(base64.b16encode(os.urandom(length // 2)).decode('utf-8').lower())

def generate_api_key() -> str:
    choices = string.ascii_letters + string.digits
    altchars = ''.join([choices[ord(os.urandom(1)) % 62] for _ in range(2)]).encode("utf-8")
    api_key = base64.b64encode(os.urandom(24), altchars=altchars).decode("utf-8")
    return api_key

def has_api_key_format(key: str) -> bool:
    return bool(re.fullmatch(r"([A-Za-z0-9]){32}", key))

def query_chunker(queries: List[Any],
                  id_collector: Optional[Set[int]]=None,
                  chunk_size: int=1000,
                  db_chunk_size: Optional[int]=None) -> Iterator[Any]:
    '''
    This merges one or more Django ascending-id queries into
    a generator that returns chunks of chunk_size row objects
    during each yield, preserving id order across all results..

    Queries should satisfy these conditions:
        - They should be Django filters.
        - They should return Django objects with "id" attributes.
        - They should be disjoint.

    The generator also populates id_collector, which we use
    internally to enforce unique ids, but which the caller
    can pass in to us if they want the side effect of collecting
    all ids.
    '''
    if db_chunk_size is None:
        db_chunk_size = chunk_size // len(queries)

    assert db_chunk_size >= 2
    assert chunk_size >= 2

    if id_collector is not None:
        assert(len(id_collector) == 0)
    else:
        id_collector = set()

    def chunkify(q: Any, i: int) -> Iterator[Tuple[int, int, Any]]:
        q = q.order_by('id')
        min_id = -1
        while True:
            assert db_chunk_size is not None  # Hint for mypy, but also workaround for mypy bug #3442.
            rows = list(q.filter(id__gt=min_id)[0:db_chunk_size])
            if len(rows) == 0:
                break
            for row in rows:
                yield (row.id, i, row)
            min_id = rows[-1].id

    iterators = [chunkify(q, i) for i, q in enumerate(queries)]
    merged_query = heapq.merge(*iterators)

    while True:
        tup_chunk = list(itertools.islice(merged_query, 0, chunk_size))
        if len(tup_chunk) == 0:
            break

        # Do duplicate-id management here.
        tup_ids = {tup[0] for tup in tup_chunk}
        assert len(tup_ids) == len(tup_chunk)
        assert len(tup_ids.intersection(id_collector)) == 0
        id_collector.update(tup_ids)

        yield [row for row_id, i, row in tup_chunk]

def process_list_in_batches(lst: List[Any],
                            chunk_size: int,
                            process_batch: Callable[[List[Any]], None]) -> None:
    offset = 0

    while True:
        items = lst[offset:offset+chunk_size]
        if not items:
            break
        process_batch(items)
        offset += chunk_size

def split_by(array: List[Any], group_size: int, filler: Any) -> List[List[Any]]:
    """
    Group elements into list of size `group_size` and fill empty cells with
    `filler`. Recipe from https://docs.python.org/3/library/itertools.html
    """
    args = [iter(array)] * group_size
    return list(map(list, zip_longest(*args, fillvalue=filler)))
