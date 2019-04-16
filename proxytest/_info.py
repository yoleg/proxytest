"""
Info-carrying objects shared between proxytest and backends.
"""

import time
from typing import Any, Callable


class SessionConfig(object):
    def __init__(self, timeout: float = None, max_workers: int = None):
        self.timeout = timeout
        self.max_workers = max_workers


class RequestInfo(object):
    @property
    def succeeded(self):
        return self.finished is not None and self.error is None

    def __init__(self, url: str, proxy_url: str = None, user_agent: str = None, name: str = None,
                 start_callback: Callable[['RequestInfo'], Any] = None, end_callback: Callable[['RequestInfo'], Any] = None):
        """
        :param url: The URL to fetch.
        :param proxy_url: The proxy to use while fetching.
        :param user_agent: The user agent to add to the headers.
        :param name: A unique name to distinguish this requests from others in logs.
        :param start_callback: Callback to call when the request starts. Will be passed one positional argument: this object.
        :param end_callback: Callback to call when the request ends. Will be passed one positional argument: this object.
        """
        if not url:
            raise ValueError('URL is required!')
        self.url = url
        self.proxy_url = proxy_url
        self.name = name or ''
        self.start_callback = start_callback
        self.end_callback = end_callback
        self.headers = {}
        if user_agent:
            self.headers['User-Agent'] = user_agent
        # variables that change during processing
        self.started = None
        """ time.monotonic() at start """
        self.finished = None
        """ time.monotonic() at end """
        self.error = None
        """ Error string """
        self.result = None
        """ Result string """

    def set_started(self):
        self.started = time.monotonic()
        if self.start_callback:
            self.start_callback(self)

    def set_finished(self, error: str = None, result: str = None):
        self.finished = time.monotonic()
        self.error = error
        self.result = result
        if self.end_callback:
            self.end_callback(self)
