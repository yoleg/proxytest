#!/usr/bin/env python3
"""
This is a simple command-line script to test if a proxy is working.

All it does is fetch a web page ("http://example.com/" by default) using the
proxies.

Project Homepage: https://github.com/yoleg/proxytest
"""
import argparse
import logging
import random
import sys
import time
from functools import partial
from typing import Iterable, Iterator

from . import backend
from .request import RequestConfig, RequestInfo, SessionInfo
from .urls import expand_proxy_url
from .version import __version__

LOGGER = logging.getLogger('proxytest')

# The URL to get via the proxy (override with the --url command-line parameter)
DEFAULT_TEST_URL = 'http://example.com/'
DEFAULT_PROXY_PORT = 8080  # default proxy port
DEFAULT_TIMEOUT = 2  # default request timeout
DEFAULT_PRINT_FORMAT = 'Content from {log_key}: "{result_flat:.100}..."'

# when the NO_PROXY string is passed in as a proxy URL, calls the webpage
# directly without a proxy
NO_PROXY = 'none'

# a random User Agent will be chosen from this list (source: "howdoi")
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0',
    'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
    'Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
]

# logging templates
LOG_FORMAT_DEFAULT = '{levelname}: {message}'
LOG_FORMAT_VERBOSE = '{asctime}.{msecs:03.0f}-{levelname}: {name}: {message}'
LOG_DATE_FORMAT = '%y/%m/%d %H:%M:%S'


# exit codes namespace
class ExitCode:
    success = 0
    fail = 1
    unable_to_test = 2


class UnableToTest(Exception):
    """ If raised, will return ExitCode.unable_to_test"""

    def __init__(self, message: str, log_traceback: bool = False) -> None:
        self.log_traceback = log_traceback
        super().__init__(message)


# the entry point for command-line use
def main() -> int:
    """ Run the program from the command line, returning an exit code."""
    try:
        # separate out the body of the try block for clarity
        return run_from_command_line()
    except UnableToTest as e:
        LOGGER.critical('Could not run tests: {}'.format(e),
                        exc_info=e.log_traceback)
        return ExitCode.unable_to_test
    except (KeyboardInterrupt, SystemExit):
        # ensure consistent return code (and no traceback) if cancelled
        return ExitCode.unable_to_test


def run_from_command_line() -> int:
    # find and load backends (including third-party extensions)
    # see backend.py
    backend.find_backends()

    # get command line parser
    # backends should have been loaded already (for the --help option)
    parser = get_argument_parser()

    # options such as --help may raise SystemExit here
    options = parser.parse_args()

    # configure logging
    _configure_logging(options)

    # run the program
    runner = Runner(options)
    try:
        runner.run()
    except (KeyboardInterrupt, SystemExit):
        if runner.running:
            raise  # interrupted while still running
        # otherwise if the program is interrupted while the runner has finished
        # a batch,(such as while waiting to repeat), then we can simply return
        # a normal return code

    return ExitCode.fail if runner.failed_count else ExitCode.success


class Runner(object):
    """ Processes the options and runs the requests. """

    @property
    def running(self) -> bool:
        return bool(self.start_time)

    @property
    def request_count(self) -> int:
        return len(self.context.requests)

    def __init__(self, options):
        """
        :param options: Object with options set as attributes
                        (such as from argparse).
        """
        # parse options
        self.context = _create_context(options)
        """:type: backend.SessionInfo """
        self.backend_name = options.backend
        """:type: str """
        self.backend_processor = _get_backend_processor(name=self.backend_name)
        """:type: backend.BackendInterface """
        self.repeat_seconds = options.repeat_seconds
        """ 
        How long (in seconds) to wait between runs, or falsey for no repeat. 
        """
        self.callbacks = Output()  # keep output logic separate

        # counters for statistics
        self.start_time = 0
        self.failed_count = 0
        self.ran_count = 0

    def run(self):
        """
        Runs either once or forever, depending on self.repeat_seconds
        """
        while True:
            self.run_once()
            if not self.repeat_seconds:
                # return after first run if no need to repeat
                return
            self.callbacks.runner_waiting(self.repeat_seconds)
            # this blocks main thread (this is OK because nothing else is
            # expected to be running)
            time.sleep(self.repeat_seconds)

    def run_once(self):
        """
        Run the backend processor, gathering statistics.

        :raises: UnableToTest on error
        """
        self.start_time = time.monotonic()  # indicates "is running"
        self.callbacks.run_start(self, start_time=self.start_time)
        try:
            # all backend processors are expected to accept a single object as
            # a positional argument
            self.backend_processor(self.context)
        except Exception as e:
            raise UnableToTest('Error running processor {}: {}'.format(self.backend_name, e))

        # a valid backend would finish all of the requests
        unfinished_count = sum((1 for x in self.context.requests if not x.status.finished))
        if unfinished_count:
            raise UnableToTest('{} out of {} requests unfinished!'.format(unfinished_count, self.request_count))

        # log stats
        self.failed_count += sum((1 for x in self.context.requests if not x.status.succeeded))
        self.ran_count += self.request_count
        self.callbacks.run_end(self, start_time=self.start_time)
        self.start_time = 0  # indicates "no longer running"


def _get_backend_processor(name: str) -> backend.BackendInterface:
    """
    Gets the backend processor callable from the registry.

    :raises: UnableToTest if the processor is invalid
    """
    if not backend.REGISTRY:
        raise UnableToTest('No backends available! Try installing one of the '
                           'following packages: {}' +
                           ', '.join(backend.SUGGESTED_PACKAGES))
    processor = backend.REGISTRY.get(name, None)
    """ :type: backend.BackendInterface """
    if not callable(processor):
        available_backends = ', '.join(sorted(backend.REGISTRY))
        raise UnableToTest('Invalid processor in backend {}: {!r}! '
                           'Available backends: {}'.format(name, processor, available_backends))
    return processor


def _create_context(options) -> SessionInfo:
    # create the context object to pass to the backend
    try:
        requests = list(_make_requests_from_options(options))
        """:type: list[RequestInfo] """
    except ValueError:
        # detailed error(s) already logged in _make_requests_from_options
        raise UnableToTest('Invalid configuration!')

    context = SessionInfo(
            # repeat as arguments for easy IDE inspections (instead of just passing in options)
            timeout=options.timeout,
            max_workers=options.workers,
            requests=requests,
    )
    return context


def _non_negative_argument(value: int, cls: type):
    """ argparse type= argument for numeric types that cannot be negative."""
    try:
        value = cls(value or 0)  # None same as zero
    except TypeError:
        raise argparse.ArgumentTypeError('Expected an {}, got {}'.format(cls.__name__, value))
    if value < 0:
        raise argparse.ArgumentTypeError('Expected positive {}, got {}'.format(cls.__name__, value))
    return value


integer_argument = partial(_non_negative_argument, cls=int)
float_argument = partial(_non_negative_argument, cls=float)


def get_argument_parser() -> argparse.ArgumentParser:
    """
    Parse command-line options.

    The backends should been loaded already (to determine choices, default value, and help text for the --backend option)
    """

    description = 'Test if one or more HTTP proxies are working by requesting a webpage through each.'
    epilog = 'Return status: 0 on success, 1 if any proxy tests failed, ' \
             'or 2 if an error prevented any proxy tests from starting or finishing.'
    parser = argparse.ArgumentParser('proxytest', description=description, epilog=epilog)

    # show version and exit
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(__version__))

    # required arguments - variable number of proxy URLs
    parser.add_argument('proxies', metavar='PROXYHOST:STARTPORT[-ENDPORT]', type=str, nargs='+',
                        help='The proxy host/ports to use. -ENDPORT is optional. '
                             'Example: 1.2.3.4:8080 1.2.3.4:8080-8090. '
                             'Use "{}" to call the webpage directly.'.format(NO_PROXY))

    # optional arguments
    parser.add_argument('--agent', '-a', dest='agent', type=str,
                        help='The user agent string to use. (default: random)')

    # which backend to use
    available_backends = sorted(backend.REGISTRY)
    default_backend = 'aiohttp' if 'aiohttp' in backend.REGISTRY else (available_backends and available_backends[0] or 'None available!')
    also_text = ''
    if backend.SUGGESTED_PACKAGES:
        also_text = 'For more backends, install: {}'.format(', '.join(backend.SUGGESTED_PACKAGES))
    backend_help = 'The backend to use. Choose from: {choices}. {also_text} (default: {default})'.format(
            choices=', '.join(available_backends) or 'None available!',
            also_text=also_text,
            default=default_backend,
    )
    parser.add_argument('--backend', '-b', dest='backend', type=str, choices=available_backends, default=default_backend, help=backend_help)

    # request configuration options
    parser.add_argument('--number', '-n', dest='number', type=integer_argument, default=1,
                        help='Number of times to test each proxy (default: 1)')
    parser.add_argument('--repeat', '-r', metavar='SECONDS', dest='repeat_seconds', type=float_argument, default=0,
                        help='Continue running and repeat the test every X seconds')
    parser.add_argument('--timeout', '-t', dest='timeout', type=float_argument, default=DEFAULT_TIMEOUT,
                        help='Timeout in seconds for each request. (default: {})'.format(DEFAULT_TIMEOUT))
    parser.add_argument('--url', '-u', dest='test_url', type=str, default=DEFAULT_TEST_URL,
                        help='The URL of the webpage to get. (default: {!r}).'.format(DEFAULT_TEST_URL))
    parser.add_argument('--workers', '-j', dest='workers', type=integer_argument, default=0,
                        help='Max number of concurrent requests. (default: unlimited)')

    # stdout/ stderr options
    group = parser.add_argument_group('output')
    group.add_argument('--print', '-p', dest='print', action='store_true',
                       help='Print each webpage to stdout on a successful fetch.')
    placeholders = RequestInfo(RequestConfig('_')).get_placeholders()
    group.add_argument('--format', '-f', dest='print_format', type=str, default=DEFAULT_PRINT_FORMAT,
                       help='The output format to use for --print. '
                            'Placeholders: {}. (default: {!r})'.format(
                               ', '.join(sorted(placeholders)), DEFAULT_PRINT_FORMAT))
    group.add_argument('--quiet', '-q', dest='quiet', action='store_true',
                       help='Suppress logging. Overrides --debug and --verbose, '
                            'but --print will still work.')
    group.add_argument('--debug', '-d', dest='debug', action='store_true',
                       help='Enable debug logging to stderr. Overrides --verbose.')
    group.add_argument('--verbose', '-v', dest='verbose', action='store_true',
                       help='Enable verbose logging to stderr. ')
    return parser


def _configure_logging(options):
    """ configure logging to stream output """
    handler = logging.StreamHandler(sys.stderr)
    log_format = LOG_FORMAT_DEFAULT
    log_level = logging.WARNING
    if options.quiet:
        handler = logging.NullHandler()
    elif options.debug:
        log_level = logging.DEBUG
        log_format = LOG_FORMAT_VERBOSE
    elif options.verbose:
        log_level = logging.INFO
        log_format = LOG_FORMAT_VERBOSE
    logging.basicConfig(
            level=log_level,
            format=log_format,
            datefmt=LOG_DATE_FORMAT,
            style='{',
            handlers=[handler]
    )


def _make_requests_from_options(options) -> Iterator[RequestInfo]:
    """ Convert command-line proxy URLs to request configuration objects. """
    start_callback = Output.request_start
    print_template = '' if not options.print else options.print_format

    def end_callback(request: RequestInfo):
        return Output.request_end(request, print_template=print_template)

    # create multiple requests for the same proxy if options.number > 1
    for _ in range(0, options.number):
        iterator = _expand_proxy_urls(options.proxies)
        for i, proxy_url in enumerate(iterator):
            config = RequestConfig(
                    # name for easy ID in logs
                    name='request{} ({})'.format(i, proxy_url or 'no proxy'),

                    # request options
                    proxy_url=proxy_url or None,
                    url=options.test_url,
                    user_agent=options.agent or random.choice(USER_AGENTS),

                    # callbacks keep output logic out of RequestConfig
                    start_callback=start_callback,
                    end_callback=end_callback,
            )
            yield RequestInfo(config)


def _expand_proxy_urls(proxy_strings: Iterable[str]) -> Iterator[str]:
    """
    Convert command-line proxy inputs to valid proxy URLs

    :returns: iterator of URLs (or empty strings for NO_PROXY)
    :raises: ValueError if any are invalid
    """
    for proxy_string in proxy_strings:
        if proxy_string == NO_PROXY:
            yield ''
            continue
        try:
            # expand shorthand proxy URLs such as '1.2.3.4:8080-8084'
            yield from expand_proxy_url(proxy_string, default_port=DEFAULT_PROXY_PORT)
        except ValueError as e:
            raise Exception('Invalid proxy {!r} ({})'.format(proxy_string, str(e) or repr(e)))


class Output:  # here, the class is just a tidy namespace, but it can be extended
    """ A namespace to keep all of the output logic in one place and easy to extend."""

    @staticmethod
    def runner_waiting(seconds: float):
        LOGGER.info('Waiting for {:.2f}s before repeating. Use CTRL+C to exit.'.format(seconds))

    # noinspection PyUnusedLocal
    @classmethod
    def run_start(cls, runner: Runner, start_time: float):
        LOGGER.info('Starting {} requests using {}.'.format(runner.request_count, runner.backend_name))

    @classmethod
    def run_end(cls, runner: Runner, start_time: float):
        end_time = time.monotonic() - start_time
        LOGGER.info('SUMMARY: {failed}/{ran} requests failed ({percent:.1f}%) in {duration:.2f}s.'.format(
                failed=runner.failed_count,
                ran=runner.ran_count,
                percent=(runner.failed_count / runner.ran_count) * 100,
                duration=end_time,
        ))

    @staticmethod
    def request_start(request: RequestInfo):
        """ log start of request. """
        data = request.get_placeholders()
        LOGGER.info('{log_key}: Connecting to {url}'.format(**data))

    @staticmethod
    def request_end(request: RequestInfo, print_template: str = ''):
        """ log end of request. """
        status = request.status
        data = request.get_placeholders()
        duration = status.finished - status.started

        # warn if failed
        if not status.succeeded:
            LOGGER.warning('{log_key}: Error connecting to {url}: {error} ({duration:.2f}s)'.format(duration=duration, **data))
            return

        # log and optionally dump content on success
        LOGGER.info('{log_key}: Success! Got {length} characters from {url} ({duration:.2f}s)'.format(
                length=len(status.result), duration=duration, **data))
        if print_template:
            print(print_template.format(
                    result_flat=' '.join(str(status.result).splitlines()),
                    duration=duration,
                    **data
            ))
