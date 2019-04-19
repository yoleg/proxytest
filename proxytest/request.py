"""
A minimal interface for all of the information (configuration and state)
that must be shared between the caller and the backend.
"""

import time
from typing import Any, Callable, Dict, List


class SessionInfo(object):
    """
    A single object to share with the backend.

    Contains both state and configuration.
    """

    def __init__(self, *, requests: List['RequestInfo'] = None, timeout: float = None, max_workers: int = None):
        self.timeout = timeout
        self.max_workers = max_workers
        self.requests = requests or []
        """:type: list[RequestInfo] """


class RequestInfo(object):
    def __init__(self, config: 'RequestConfig'):
        self.config = config
        """:type: RequestConfig"""
        self.status = RequestStatus()
        """:type: RequestStatus"""

    def get_placeholders(self) -> Dict[str, Any]:
        data = {}
        data.update(self.config.__dict__)
        data.update(self.status.__dict__)
        return data

    def __str__(self):
        return self.config.name

    def __repr__(self):
        return 'RequestInfo({!r}, {!r})'.format(self.config, self.status)

    def start(self):
        self.status.start()
        if self.config.start_callback:
            self.config.start_callback(self)

    def finish(self, error: Exception = None, result: str = None, status_code: int = None):
        self.status.finish(error=error, result=result, status_code=status_code)
        if self.config.end_callback:
            self.config.end_callback(self)


class RequestStatus(object):
    """ Request status. Changes only between start() and finish().. """
    @property
    def succeeded(self):
        assert self.finished, 'succeeded called before finished! started={!r}, finished={!r}'.format(self.started, self.finished)
        return self.error is None

    def __init__(self):
        # variables that change during processing
        self.started = None
        """ time.monotonic() at start """
        self.finished = None
        """ time.monotonic() at end """
        self.error = None
        """ Error string """
        self.result = None
        """ Result string """
        self.status_code = None
        """ Result string """

    def __str__(self):
        if not self.started:
            return 'unstarted'
        if not self.finished:
            return 'running'
        if self.succeeded:
            return 'succeeded'
        return 'error: {}'.format(self.error)

    def __repr__(self):
        return ', '.join('{}={}'.format(k, v) for k, v in sorted(self.__dict__))

    def start(self):
        assert not self.finished, repr(self)
        self.started = time.monotonic()

    def finish(self, error: Exception = None, result: str = None, status_code: int = None):
        assert self.started, repr(self)
        self.finished = time.monotonic()
        self.error = None if not error else (str(error) or repr(error))
        self.result = result
        self.status_code = status_code


class RequestConfig(object):
    """ Request configuration. Should not change after start. """

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

    def __repr__(self):
        return ', '.join('{}={}'.format(k, v) for k, v in sorted(self.__dict__))

    __str__ = __repr__
