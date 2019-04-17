#!/usr/bin/env python3
"""
This is a simple command-line script to test if a proxy is working.

All it does is fetch a web page ("http://example.com/" by default) using the proxies.

Project Homepage: https://github.com/yoleg/proxytest
"""
import logging
import random
import sys

import argparse
import time
from typing import Any, Callable, List, Optional

from .request import RequestInfo, SessionConfig
from .urls import expand_proxy_url
from .version import __version__

# The URL to get via the proxy (override with the --url command-line parameter)
DEFAULT_TEST_URL = 'http://example.com/'
DEFAULT_PROXY_PORT = '8080'  # default proxy port
DEFAULT_TIMEOUT = 2  # default request timeout
DEFAULT_PRINT_FORMAT = 'Content from {name}: "{result_flat:.100}..."'  # --print output format

# a random User Agent will be chosen from this list (source: "howdoi")
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0',
    'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
    'Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
]

# logging configuration
LOG_FORMAT_DEFAULT = '{levelname}: {message}'
LOG_FORMAT_VERBOSE = '{asctime}.{msecs:03.0f}-{levelname}: {name}: {message}'
LOG_DATE_FORMAT = '%y/%m/%d %H:%M:%S'
LOGGER = logging.getLogger('proxytest')


# exit codes namespace
class ExitCode:
    success = 0
    fail = 1
    unable_to_test = 2


# event namespace
class Event:
    request_start = 'start'
    request_end = 'end'


BackendProcessor = Callable[[List[RequestInfo], Optional[SessionConfig]], Any]

_not_installed = []
""" List of uninstalled packages that would add backend options. """

backends = {}
"""
backend-type to processor function

:type: dict[str, BackendProcessor]
"""


def _gather_backends():
    if sys.version_info >= (3, 5):
        try:
            # noinspection PyPackageRequirements
            import aiohttp
        except ImportError:
            _not_installed.append('aiohttp')
        else:
            from .backend_aiohttp import process_requests
            backends['aiohttp'] = process_requests

    try:
        # noinspection PyPackageRequirements
        import requests
    except ImportError:
        _not_installed.append('requests')
    else:
        from .backend_requests import process_requests
        backends['requests'] = process_requests


_gather_backends()


def main() -> int:
    """ Run the program from the command line, returning an exit code."""
    options = _process_command_line()

    _configure_logging(options)

    if not backends:
        LOGGER.critical('No backends available! Try installing one of the following packages: {}'.format(', '.join(_not_installed)))
        return ExitCode.unable_to_test

    request_infos = _make_requests_from_options(options)
    if not request_infos:
        return ExitCode.unable_to_test

    session_config = SessionConfig(
            timeout=options.timeout,
            max_workers=options.workers,
    )

    # choose the backend to use
    backend = options.backend
    backend_processor = backends.get(backend)
    """ :type: BackendProcessor """
    if not backend_processor:
        available_backends = ', '.join(sorted(backends))
        LOGGER.critical('Invalid backend {}! Available backends: {}'.format(backend, available_backends))
        return ExitCode.unable_to_test

    # run the tests
    LOGGER.info('Starting tests on {} proxies using {}.'.format(len(request_infos), backend))
    start_time = time.monotonic()
    assert callable(backend_processor), repr(backend_processor)
    backend_processor(request_infos, session_config)
    unfinished_count = sum((1 for x in request_infos if not x.finished))
    if unfinished_count:
        LOGGER.critical('{} proxies untested out of {} proxies needed'.format(unfinished_count, len(request_infos)))
        return ExitCode.unable_to_test

    fail_count = sum((1 for x in request_infos if not x.succeeded))
    LOGGER.info('Done! {} proxies failed out of {} proxies tested in {:.2f}s'.format(fail_count, len(request_infos), time.monotonic() - start_time))

    # choose the exit code (0 on success)
    # noinspection PyShadowingNames
    exit_code = ExitCode.fail if fail_count else ExitCode.success
    return exit_code


def _process_command_line():
    available_backends = sorted(backends)
    default_backend = 'aiohttp' if 'aiohttp' in backends else (available_backends and available_backends[0] or 'None available!')

    parser = argparse.ArgumentParser('proxytest',
                                     description='Test if one or more HTTP proxies are working by requesting a webpage through each.',
                                     epilog='Return status: 0 on success, 1 if any proxy tests failed, or 2 if an error prevented any proxy tests from starting or finishing.'
                                     )
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))
    parser.add_argument('proxies', metavar='PROXYHOST:STARTPORT[-ENDPORT]', type=str, nargs='+',
                        help='The proxy host/ports to use. -ENDPORT is optional. Example: 1.2.3.4:8080 1.2.3.4:8080-8090')
    parser.add_argument('--agent', '-a', dest='agent', type=str,
                        help='The user agent string to use. (default: random)')
    parser.add_argument('--backend', '-b', dest='backend', type=str, choices=available_backends, default=default_backend,
                        help='The backend to use. Choose from: {choices}. {also_text} (default: {default})'.format(
                                choices=', '.join(available_backends) or 'None available!',
                                also_text=('' if not _not_installed else 'For more backends, install: {}'.format(', '.join(_not_installed))),
                                default=default_backend)
                        )
    parser.add_argument('--debug', '-d', dest='debug', action='store_true',
                        help='Enable debug output.')
    parser.add_argument('--number', '-n', dest='number', type=int, default=1,
                        help='Number of times to test each proxy (default: 1)')
    parser.add_argument('--print', '-p', dest='print', action='store_true',
                        help='Print each webpage to stdout on a successful fetch.')
    placeholders = sorted(list(RequestInfo('_').__dict__) + ['result_flat', 'duration'])
    parser.add_argument('--format', '-f', dest='print_format', type=str, default=DEFAULT_PRINT_FORMAT,
                        help='The output format to use for --print. Placeholders: {}. (default: {!r})'.format(', '.join(placeholders), DEFAULT_PRINT_FORMAT))
    parser.add_argument('--timeout', '-t', dest='timeout', type=float, default=DEFAULT_TIMEOUT,
                        help='Timeout in seconds for each request. (default: {})'.format(DEFAULT_TIMEOUT))
    parser.add_argument('--url', '-u', dest='test_url', type=str, default=DEFAULT_TEST_URL,
                        help='The URL of the webpage to get. (default: {!r}).'.format(DEFAULT_TEST_URL))
    parser.add_argument('--workers', '-j', dest='workers', type=int, default=0,
                        help='Max number of concurrent requests. (default: unlimited)')
    parser.add_argument('--verbose', '-v', dest='verbose', action='store_true',
                        help='Enable verbose output.')
    options = parser.parse_args()
    return options


def _configure_logging(options):
    """ configure logging to stream output """
    if options.debug:
        log_level = logging.DEBUG
        log_format = LOG_FORMAT_VERBOSE
    elif options.verbose:
        log_level = logging.INFO
        log_format = LOG_FORMAT_VERBOSE
    else:
        log_level = logging.INFO + 1
        log_format = LOG_FORMAT_DEFAULT
    logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=LOG_DATE_FORMAT,
            style='{'
    )


def _make_requests_from_options(options) -> List[RequestInfo]:
    """ Convert command-line proxy URLs to request configuration objects. """
    request_infos = []
    valid = True
    i = 0
    for proxy_string in options.proxies:
        try:
            # expand shorthand proxy URLs such as '1.2.3.4:8080-8084'
            for proxy_url in expand_proxy_url(proxy_string):
                # create multiple requests for the same proxy if options.number > 1
                for _ in range(0, options.number):
                    i += 1
                    request_info = RequestInfo(
                            name='request{}'.format(i),
                            proxy_url=proxy_url,
                            url=options.test_url,
                            user_agent=options.agent or random.choice(USER_AGENTS),
                            start_callback=lambda request: _event_callback(request, options=options, event=Event.request_start),
                            end_callback=lambda request: _event_callback(request, options=options, event=Event.request_end),
                    )
                    request_infos.append(request_info)
        except ValueError as e:
            valid = False
            LOGGER.error('Invalid proxy {}: {}'.format(repr(proxy_string), e))
    if not valid:
        return []
    if not request_infos:
        LOGGER.error('No proxies to test!')
    return request_infos


def _event_callback(request: RequestInfo, options, event: str = None):
    """ Handling for request start/ error/ success. """
    string_to = request.url + (' directly' if not request.proxy_url else ' via proxy {}'.format(repr(request.proxy_url)))
    if event == Event.request_start:
        LOGGER.info('{name}: Connecting to {string_to}'.format(string_to=string_to, name=request.name))
        return

    assert event == Event.request_end, event
    duration = request.finished - request.started

    # warn if failed
    if not request.succeeded:
        LOGGER.warning('{name}: Error connecting to {string_to}: {error} ({duration:.2f}s)'.format(name=request.name, error=request.error, duration=duration, string_to=string_to))
        return

    # log and optionally dump content on success
    LOGGER.info('{name}: Success! Got {length} characters from {string_to} ({duration:.2f}s)'.format(length=len(request.result), name=request.name, duration=duration, string_to=string_to))
    if options.print:
        print(options.print_format.format(
                result_flat=' '.join(str(request.result).splitlines()),
                duration=duration,
                **request.__dict__
        ))
