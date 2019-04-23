"""
The requests backend (request processor).

Uses threading for concurrency.

Requires "requests" package. Useful for Python 3.4. Supports https proxies, unlike aiohttp (as of aiohttp 3.5.4).
"""

from proxytest import backend, parallel
from proxytest.context import ProxyTestContext, RequestInfo

try:
    # noinspection PyPackageRequirements
    import requests
except ImportError:
    raise backend.MissingDependenciesError(['requests'])


class RequestsBackend(backend.AbstractBackend):
    """ Backend that uses the "requests" module for fetching the webpage. """
    name = 'requests'

    def process(self, context: ProxyTestContext):
        """ Process the requests in parallel using requests."""
        with requests.Session() as session:  # cleanup when done
            # parallel.process_requests example using closure
            def _process(request: RequestInfo):
                self._process_request(request, session=session, timeout=context.timeout)

            parallel.process_requests(
                    requests=context.requests,
                    callback=_process,
                    max_workers=context.max_workers
            )

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
