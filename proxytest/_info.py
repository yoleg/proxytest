"""
Info-carrying objects used by multiple modules.
"""

import logging
import time


class SessionConfig(object):
    def __init__(self, timeout: float=None, max_workers: int=None):
        self.timeout = timeout
        self.max_workers = max_workers


class RequestInfo(object):
    @property
    def prefix(self):
        """ The log message prefix """
        return self.name and '{}: '.format(self.name)

    def __init__(self, url: str, proxy_url: str = None, user_agent: str = None, logger: logging.Logger=None, name: str=None, timeout: int=None):
        if not url:
            raise ValueError('URL is required!')
        self.url = url
        self.proxy_url = proxy_url
        self.logger = logger
        self.headers = {}
        if user_agent:
            self.headers['User-Agent'] = user_agent
        self.string_to = url + (' directly' if not proxy_url else ' via proxy {}'.format(repr(proxy_url)))
        self.name = name or ''
        """ Distinguish this requests from others in logs, etc... """
        self.timeout = timeout
        # variables that change during processing
        self.started = 0
        """ time.monotonic() at start """
        self.finished = 0
        """ time.monotonic() at end """
        self.error = None
        """ Error string """
        self.result = None
        """ Result string """

    def set_started(self):
        self.started = time.monotonic()
        if not self.logger:
            return
        self.logger.info('{}Connecting to {}'.format(self.prefix, self.string_to))

    def set_finished(self, error: str=None, result: str=None):
        self.finished = time.monotonic()
        self.error = error
        self.result = result
        if not self.logger:
            return
        duration = self.finished - self.started
        if error:
            self.logger.error('{self.prefix}Error connecting to {self.string_to}: {error} ({duration:.2f}s)'.format(self=self, error=error, duration=duration))
        else:
            self.logger.info('{self.prefix}Success! Connected to {self.string_to} ({duration:.2f}s)'.format(self=self, duration=duration))
