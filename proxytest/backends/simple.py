"""
A simple backend that requires only the Python standard library.

Uses threading for concurrency.
"""
import functools
import urllib.parse
import urllib.request

from proxytest import backend, parallel
from proxytest.context import ProxyTestContext, RequestConfig, RequestInfo


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
        request.start()
        try:
            result = self._get_result(config=request.config, timeout=context.timeout)
        except Exception as e:
            request.finish(error=e)
        else:
            request.finish(result=result)

    def _get_result(self, config: RequestConfig, timeout: int):
        try:
            if config.proxy_url:
                handler, auth_handler = self._get_handlers_proxy(proxy_url=config.proxy_url)
            else:
                handler, auth_handler = self._get_handlers_http()
            opener = urllib.request.build_opener(handler, auth_handler)
            opener.addheaders = list(config.headers.items())
        except Exception:
            self.log.exception('Error processing')
            raise
        try:
            # start the connection
            response = opener.open(config.url, timeout=timeout)
            _raise_for_status(status_code=response.status, reason=str(response.reason))
            result = response.read()
        finally:
            opener.close()
        return result

    def _get_handlers_http(self):
        handler = urllib.request.HTTPHandler()
        auth_handler = urllib.request.HTTPBasicAuthHandler()
        return handler, auth_handler

    def _get_handlers_proxy(self, proxy_url: str):
        proxy_parts = urllib.parse.urlparse(proxy_url)
        proxy_url = proxy_parts.scheme + '://' + proxy_parts.hostname + ':' + str(proxy_parts.port)
        proxies = {
            'http': proxy_url,
            'https': proxy_url,
        }
        handler = urllib.request.ProxyHandler(proxies)
        auth_handler = urllib.request.ProxyBasicAuthHandler()
        if proxy_parts.username:
            auth_handler.add_password(None, proxy_url, proxy_parts.username, proxy_parts.password)
        return auth_handler, handler


def _raise_for_status(status_code: int, reason: str):
    """ Raises an exception if HTTP response had an error status."""
    # source: https://github.com/kennethreitz/requests/blob/master/requests/models.py
    if 400 <= status_code < 500:
        raise HTTPError('{} Client Error: {}'.format(status_code, reason))
    if 500 <= status_code < 600:
        raise HTTPError('{} Server Error: {}'.format(status_code, reason))
