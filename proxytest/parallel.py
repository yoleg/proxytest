"""
convenience function for backends to use for easy parallel requests
"""
import contextlib
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List

from .context import RequestInfo


@contextlib.contextmanager
def process_requests(requests: List[RequestInfo], callback: Callable[[RequestInfo], Any], max_workers: int = None):
    """
    Call the callback for each request in a separate thread.

    :param requests: the list of requests to process
    :param callback: a callback that accepts a request as a single positional argument
    :param max_workers: 1 for blocking, 0 for unlimited, or a positive integer for max workers
    """
    max_workers = int(max_workers or 0)

    # no threads if only one worker - e.g. for easier debugging
    if max_workers == 1:
        for request in requests:
            callback(request)
        return

    # otherwise use threads
    max_workers = max_workers if max_workers > 0 else len(requests)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for request in requests:
            executor.submit(callback, request)
