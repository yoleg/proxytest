"""
The requests backend (request processor).

Uses threading for concurrency.

Requires "requests" package. Useful for Python 3.5.3 and below.
"""
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

# noinspection PyPackageRequirements
import requests

from ._info import RequestInfo, SessionConfig

LOGGER = logging.getLogger('proxytest.requests')


def process_requests(request_infos: List[RequestInfo], config: SessionConfig):
    """ Process the requests in parallel using requests."""
    session = requests.Session()
    processor = functools.partial(_process_request, session=session, timeout=config.timeout)

    # no threads if only one worker
    if config.max_workers == 1:
        for request in request_infos:
            processor(request=request)
        return

    # otherwise use threads
    with ThreadPoolExecutor(max_workers=config.max_workers or len(request_infos)) as executor:
        for request in request_infos:
            executor.submit(processor, request)


def _process_request(request: RequestInfo, session: requests.Session, timeout: float = None):
    """ Make a GET request to the URL, optionally using a proxy URL."""
    proxies = None
    if request.proxy_url:
        proxies = {
            'http': request.proxy_url,
            'https': request.proxy_url,
        }
    request.set_started()
    try:
        response = session.request('GET', url=request.url, headers=request.headers,
                                   proxies=proxies, allow_redirects=True, timeout=timeout)
    except Exception as e:
        request.set_finished(error=str(e))
    else:
        request.set_finished(result=response.text)
