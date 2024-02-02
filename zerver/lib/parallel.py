import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable, Iterable, List, Optional, Tuple, TypeVar

import bmemcached
from django.core.cache import cache
from django.db import connection

ParallelRecordType = TypeVar("ParallelRecordType")
OutputRecordType = TypeVar("OutputRecordType")


def run_parallel(
    func: Callable[[ParallelRecordType], OutputRecordType],
    records: Iterable[ParallelRecordType],
    processes: int,
    *,
    initializer: Optional[Callable[..., None]] = None,
    initargs: Tuple[Any, ...] = tuple(),
    catch: bool = False,
    report_every: int = 1000,
    report: Optional[Callable[[int], None]] = None,
) -> List[OutputRecordType]:  # nocoverage
    count = 0

    assert processes > 0

    if processes == 1:
        if initializer is not None:
            initializer(*initargs)
        results = []
        for record in records:
            count += 1
            if report is not None and count % report_every == 0:
                report(count)
            if catch:
                try:
                    results.append(func(record))
                except Exception:
                    logging.exception("Error processing item: %s", record, stack_info=True)
            else:
                results.append(func(record))
        return results

    # Close our database connections, so our forked children do not
    # share them.  Django will transparently re-open them as needed.
    connection.close()
    _cache = cache._cache  # type: ignore[attr-defined] # not in stubs
    assert isinstance(_cache, bmemcached.Client)
    _cache.disconnect_all()

    with ProcessPoolExecutor(
        max_workers=processes, initializer=initializer, initargs=initargs
    ) as executor:
        futures = [executor.submit(func, record) for record in records]
        for future in as_completed(futures):
            count += 1
            if report is not None and count % report_every == 0:
                report(count)
        results = []
        for future in futures:
            if catch and future.exception() is not None:
                # Re-raise the exception so we can log it
                try:
                    future.result()
                except Exception:
                    logging.exception("Error processing item: %s", record, stack_info=True)
            else:
                results.append(future.result())
        return results
