"""
A simple backend that requires only the Python standard library.

Uses threading for concurrency.
"""
import functools
import urllib.parse
import urllib.request

from proxytest import backend, parallel
from proxytest.context import ProxyTestContext, RequestInfo


class HTTPError(Exception):
    """ Exception raised for response status codes between 400 and 600. """
    pass


class SimpleBackend(backend.AbstractBackend):
    """ Backend that uses "http.client" for fetching the webpage. """
    name = 'simple'

    def process(self, context: ProxyTestContext):
        """ Process the requests in parallel using threads."""
        # parallel.process_requests example using partial
        # noinspection PyTypeChecker
        _processor = functools.partial(self._process_request, context=context)
        """:type: (RequestInfo) -> None """
        parallel.process_requests(
                requests=context.requests,
                callback=_processor,
                max_workers=context.max_workers
        )

    def _process_request(self, request: RequestInfo, context: ProxyTestContext):
        """ Make a GET request to the URL, optionally using a proxy URL."""
        proxies = None
        if request.config.proxy_url:
            proxies = {
                'http': request.config.proxy_url,
                'https': request.config.proxy_url,
            }
        proxy_parts = urllib.parse.urlparse(request.config.proxy_url)
        proxy_handler = urllib.request.ProxyHandler(proxies)
        proxy_auth_handler = urllib.request.ProxyBasicAuthHandler()
        if proxy_parts.username:
            proxy_auth_handler.add_password(None, request.config.proxy_url, proxy_parts.username, proxy_parts.password)
        opener = urllib.request.build_opener(proxy_handler, proxy_auth_handler)
        opener.addheaders = list(request.config.headers.items())

        # start the connection
        request.start()
        try:
            response = opener.open(request.config.url, timeout=context.timeout)
            _raise_for_status(status_code=response.status, reason=str(response.reason))
            result = response.read()
            opener.close()
        except Exception as e:
            request.finish(error=e)
        else:
            request.finish(result=result)
        finally:
            opener.close()


def _raise_for_status(status_code: int, reason: str):
    """ Raises an exception if HTTP response had an error status."""
    # source: https://github.com/kennethreitz/requests/blob/master/requests/models.py
    if 400 <= status_code < 500:
        raise HTTPError('{} Client Error: {}'.format(status_code, reason))
    if 500 <= status_code < 600:
        raise HTTPError('{} Server Error: {}'.format(status_code, reason))
