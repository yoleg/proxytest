"""
The requests backend (request processor).

Uses threading for concurrency.

Requires "requests" package. Useful for Python 3.4. Supports https proxies, unlike aiohttp (as of aiohttp 3.5.4).
"""
import functools
from concurrent.futures import ThreadPoolExecutor

from proxytest import backend
from proxytest.request import RequestInfo, SessionInfo

try:
    # noinspection PyPackageRequirements
    import requests
except ImportError:
    raise backend.MissingDependenciesError(['requests'])


class RequestsBackend(backend.AbstractBackend):
    name = 'requests'

    def process(self, info: SessionInfo):
        """ Process the requests in parallel using requests."""
        with requests.Session() as session:  # cleanup when done
            processor = functools.partial(self._process_request, session=session, timeout=info.timeout)

            # no threads if only one worker
            if info.max_workers == 1:
                for request in info.requests:
                    processor(request=request)
                return

            # otherwise use threads
            max_workers = info.max_workers if info.max_workers > 0 else len(info.requests)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for request in info.requests:
                    executor.submit(processor, request)

    def _process_request(self, request: RequestInfo, session: requests.Session, timeout: float = None):
        """ Make a GET request to the URL, optionally using a proxy URL."""
        proxies = None
        if request.config.proxy_url:
            proxies = {
                'http': request.config.proxy_url,
                'https': request.config.proxy_url,
            }
        request.start()
        try:
            response = session.request('GET', url=request.config.url, headers=request.config.headers,
                                       proxies=proxies, allow_redirects=True, timeout=timeout)
            response.raise_for_status()
        except Exception as e:
            request.finish(error=e)
        else:
            request.finish(result=response.text)
