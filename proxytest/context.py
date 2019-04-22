"""
A minimal interface for all of the information (configuration and state)
that must be shared between the caller and the backend.
"""

import time
from typing import Any, Callable, Dict, List, Union


# make things easier for backend implementors
def _non_negative(number: Union[int, float, None]):
    return max([0, (number or 0)])


class ProxyTestContext(object):
    """
    A single object to share with the backend processor.

    The backend processor should process all of the requests and call:
        * RequestInfo.start() before the request starts.
        * RequestInfo.finish(error=...) if the request fails, or
        * RequestInfo.finish(result=...) if the request succeeds
    """

    # options get set here explicitly as arguments for easy IDE inspections
    def __init__(self, *, requests: List['RequestInfo'] = None, timeout: float = None,
                 max_workers: int = None):  # callbacks keep this class clean and simple
        self.timeout = _non_negative(timeout)
        self.max_workers = _non_negative(max_workers)
        self.requests = requests or []
        """:type: list[RequestInfo] """


class RequestInfo(object):
    """
    Represents the configuration and state of a single request.
    """
    @property
    def log_key(self):
        """ A string to identify this request in the logs. """
        return '{} ({})'.format(self.config.name, self.config.proxy_url)

    def __init__(self, config: 'RequestConfig'):
        self.config = config
        """:type: RequestConfig"""
        self.status = RequestStatus()
        """:type: RequestStatus"""

    def get_placeholders(self) -> Dict[str, Any]:
        """ Placeholders for string formatting (e.g. for logs) """
        data = {}
        data.update(self.config.__dict__)
        data.update(self.status.__dict__)
        data['log_key'] = str(self.log_key)
        data['status'] = str(self.status)
        data['config'] = str(self.config)
        return data

    def __str__(self):
        return self.config.name

    def __repr__(self):
        return 'RequestInfo({!r}, {!r})'.format(self.config, self.status)

    def start(self):
        """ Mark this request as started and call the end_callback. """
        self.status = RequestStatus()
        """:type: RequestStatus"""
        self.status.start()
        if self.config.start_callback:
            self.config.start_callback(self)

    def finish(self, error: Exception = None, result: str = None, status_code: int = None):
        """
        Mark this request as finished and call the end_callback.

        Either error or result is required

        :param error: the Exception, on error
        :param result: the fetched text from the URL, if successful
        :param status_code: the status code of the response
        """
        if error is None and result is None:
            raise ValueError('Either error or result is required.')
        self.status.finish(error=error, result=result, status_code=status_code)
        if self.config.end_callback:
            self.config.end_callback(self)


class RequestStatus(object):
    """ Request status. Changes only between start() and finish().. """

    @property
    def succeeded(self):
        """ True if the request finished and did not have an error. """
        return self.finished and self.error is None

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
        return ', '.join('{}={}'.format(k, v) for k, v in sorted(self.__dict__.items()))

    def start(self):
        """ Mark as started. """
        assert not self.finished, repr(self)
        self.started = time.monotonic()

    def finish(self, error: Exception = None, result: str = None, status_code: int = None):
        """
        Mark this request as finished..

        :param error: the Exception, on error
        :param result: the fetched text from the URL, if successful
        :param status_code: the status code of the response
        """
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
        self.name = name or ''
        self.url = url
        self.proxy_url = proxy_url
        self.headers = {}
        if user_agent:
            self.headers['User-Agent'] = user_agent

        # callbacks keep this class clean and simple
        self.start_callback = start_callback
        self.end_callback = end_callback

    def __repr__(self):
        return ', '.join(('{}={}'.format(k, v) for k, v in sorted(self.__dict__.items())))

    __str__ = __repr__
