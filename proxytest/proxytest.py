#!/usr/bin/env python3
"""
This is a simple command-line script to test if a proxy is working.

All it does is fetch a web page ("http://example.com/" by default) using the
proxies.

The complexity here is just for demonstration and is totally unnecessary :)

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
from .context import ProxyTestContext, RequestConfig, RequestInfo
from .urls import expand_proxy_url
from .version import __version__

LOGGER = logging.getLogger('proxytest')

# The URL to get via the proxy (override with the --url command-line parameter)
DEFAULT_TEST_URL = 'http://example.com/'
DEFAULT_PROXY_PORT = 8080  # default proxy port
DEFAULT_TIMEOUT = 2  # default request timeout
DEFAULT_PRINT_FORMAT = 'Content from {proxy_url} ({idx}): "{result_flat:.100}..."'

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
LOG_FORMAT_DEFAULT = '{message}'
LOG_FORMAT_DEBUG = '{asctime}.{msecs:03.0f}: {name}: {message}'
LOG_DATE_FORMAT = '%y/%m/%d %H:%M:%S'
LOG_STREAM = sys.stderr


class ExitCode:
    """ Exit codes namespace """
    success = 0
    fail = 1
    unable_to_test = 2


class UnableToTest(Exception):
    """ If raised, will return ExitCode.unable_to_test"""

    def __init__(self, message: str, log_traceback: bool = False) -> None:
        self.log_traceback = log_traceback
        super().__init__(message)


# the entry point for command-line use
def run_from_command_line() -> int:
    """ Run the program from the command line, returning an exit code."""
    try:
        # separate out the body of the try block for clarity
        return _run_from_command_line()
    except UnableToTest as e:
        LOGGER.critical('ERROR: {}'.format(e),
                        exc_info=e.log_traceback)
        return ExitCode.unable_to_test
    except (KeyboardInterrupt, SystemExit):
        # ensure consistent return code (and no traceback) if cancelled
        return ExitCode.unable_to_test


def _run_from_command_line() -> int:
    """
    Load backends, process command-line arguments, and return an exit code.

    :raises: UnableToTest on input or system error.
    """
    # find and load backends (including third-party extensions)
    # see backend.py
    backend.find_backends()

    # get command line parser
    # backends should have been loaded already (for the --help option)
    parser = get_argument_parser()

    # options such as --help may raise SystemExit here
    options = parser.parse_args()

    # configure logging
    configure_logging(options)

    # run the program
    runner = Runner(options, callbacks=Output())
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
    """ Runs the requests based on the parsed options."""

    @property
    def running(self) -> bool:
        """ Whether the runner is still processing a batch of requests. """
        return bool(self.start_time)

    @property
    def request_count(self) -> int:
        """ The number of requests in a single batch. """
        return len(self.context.requests)

    def __init__(self, options, callbacks: 'Output' = None):
        """
        :param options: Object with options set as attributes
                        (such as from argparse or a namedtuple).
        :param callbacks: methods to call on events, such as request start/ end
        """
        self.callbacks = callbacks or Output()  # decouples output logic
        """ event callbacks """
        self.repeat_seconds = options.repeat_seconds
        """ How long (in seconds) to wait between runs, or falsey for no repeat. """

        # find and wrap the backend processor
        self.backend = self.Backend(name=options.backend)

        # build the context to pass to the backend
        builder = self.ContextBuilder(options=options, callbacks=self.callbacks)
        builder.build()
        self.context = builder.context
        """ :type: backend.ProxyTestContext """

        # counters for statistics
        self.start_time_all_runs = 0
        """ When the first run was started. """
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
        self.start_time_all_runs = self.start_time_all_runs or self.start_time
        self.callbacks.run_start(self, start_time=self.start_time)
        try:
            # all backend processors are expected to accept a single object as
            # a positional argument
            self.backend.processor(self.context)
        except Exception as e:
            raise UnableToTest('Error running processor {}: {}'
                               .format(self.backend.name, e), log_traceback=True)

        # a valid backend would finish all of the requests
        unfinished_count = sum((1 for x in self.context.requests if not x.status.finished))
        if unfinished_count:
            raise UnableToTest('{} out of {} requests unfinished!'.format(unfinished_count, self.request_count))

        # log stats
        self.failed_count += sum((1 for x in self.context.requests if not x.status.succeeded))
        self.ran_count += self.request_count
        self.callbacks.run_end(self, start_time=self.start_time)
        self.start_time = 0  # indicates "no longer running"

    class Backend:
        """ A simple wrapper for the backend processor. """

        def __init__(self, name: str):
            """
            Gets the backend processor callable from the registry.

            :raises: UnableToTest if the processor is invalid
            """
            self.name = name
            self.processor = self._find_processor()

        def _find_processor(self) -> backend.ProcessorInterface:
            if not backend.REGISTRY:
                raise UnableToTest('No backends available! Try installing '
                                   'one of the following packages: {}' +
                                   ', '.join(backend.SUGGESTED_PACKAGES))
            available_msg = 'Available backends: ' + ', '.join(sorted(backend.REGISTRY))
            try:
                processor = backend.REGISTRY[self.name]
                """ :type: backend.ProcessorInterface """
            except KeyError:
                raise UnableToTest('Backend {!r} is not available. {}'
                                   .format(self.name, available_msg))
            if not callable(processor):
                raise UnableToTest('Invalid processor in backend {}: {!r}! {}'
                                   .format(self.name, processor, available_msg))
            return processor

    class ContextBuilder:
        """
        Builds the ProxyTestContext instance.

        Allows easy replacement of context creation logic while keeping
        it in associated with its logical parent.
        """

        def __init__(self, options, callbacks: 'Output'):
            self.options = options
            self.callbacks = callbacks
            self.context = ProxyTestContext()

        def build(self):
            """ let's pretend this is super-complex """
            self.build_options()
            self.build_requests()

        def build_options(self):
            """ Build the super-complex options """
            self.context.timeout = self.options.timeout
            self.context.max_workers = self.options.workers

        def build_requests(self):
            """ Build the list of requests. """
            try:
                self.context.requests = list(self._make_requests_from_options())
            except ValueError as e:
                raise UnableToTest('Invalid configuration: {}'.format(e))

        def _make_requests_from_options(self) -> Iterator[RequestInfo]:
            """ Convert command-line proxy URLs to request configuration objects. """
            options = self.options
            start_callback = self.callbacks.request_start
            print_template = '' if not options.print else options.print_format

            # noinspection PyMissingOrEmptyDocstring
            def end_callback(request: RequestInfo):
                return self.callbacks.request_end(request, print_template=print_template)

            # create multiple requests for the same proxy if options.number > 1
            for _ in range(0, options.number):
                iterator = self._expand_proxy_urls(options.proxies)
                for i, proxy_url in enumerate(iterator):
                    config = RequestConfig(
                            # name for easy ID in logs
                            idx=i,

                            # request options
                            proxy_url=proxy_url or None,
                            url=options.test_url,
                            user_agent=options.agent or random.choice(USER_AGENTS),

                            # callbacks keep output logic out of RequestConfig
                            start_callback=start_callback,
                            end_callback=end_callback,
                    )
                    yield RequestInfo(config)

        @staticmethod
        def _expand_proxy_urls(proxy_strings: Iterable[str]) -> Iterator[str]:
            """
            Convert shorthand proxy inputs to valid proxy URLs

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
    backend_order = sorted((x for x in backend.REGISTRY if x != 'dummy'))
    backend_order.append('dummy')
    default_backend = backend_order[0]
    also_text = ''
    if backend.SUGGESTED_PACKAGES:
        also_text = 'For more backends, install: {}'.format(', '.join(backend.SUGGESTED_PACKAGES))
    backend_help = 'The backend to use. Choose from: {choices}. {also_text} (default: {default})'.format(
            choices=', '.join(available_backends) or 'None available!',
            also_text=also_text,
            default=default_backend,
    )
    parser.add_argument('--backend', '-b', dest='backend', type=str, default=default_backend, help=backend_help)

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


class ANSIIColors:
    """
    ANSII terminal colors

    Source: https://misc.flogisoft.com/bash/tip_colors_and_formatting
    """
    BLACK = '\033[30m'
    RED_DARK = '\033[31m'
    GREEN_DARK = '\033[32m'
    YELLOW_DARK = '\033[33m'
    BLUE_DARK = '\033[34m'
    MAGENTA_DARK = '\033[35m'
    CYAN_DARK = '\033[36m'
    LIGHT_GREY = '\033[37m'

    GREY_DARK = '\033[90m'
    RED_LIGHT = '\033[91m'
    GREEN_LIGHT = '\033[92m'
    YELLOW_LIGHT = '\033[93m'
    BLUE_LIGHT = '\033[94m'
    MAGENTA_LIGHT = '\033[95m'
    CYAN_LIGHT = '\033[96m'
    WHITE = '\033[97m'

    DEFAULT = '\033[39m'
    END = '\033[0m'


class ProxyTestLogFormatter(logging.Formatter):
    """ Simple colorization of log output. """

    def formatMessage(self, record: logging.LogRecord) -> str:
        """ Format and colorize the log record. """
        formatted = self._style.format(record)
        if sys.stdout.isatty():
            formatted = self._wrap_in_color(formatted, record)
        return formatted

    def _wrap_in_color(self, message, record):
        if record.levelno < logging.INFO:
            color = ANSIIColors.GREY_DARK
        elif record.levelno < logging.WARNING:
            color = ANSIIColors.DEFAULT
        elif record.levelno < logging.ERROR:
            color = ANSIIColors.YELLOW_LIGHT
        else:
            color = ANSIIColors.YELLOW_LIGHT
        message = color + message + ANSIIColors.END
        return message


def configure_logging(options):
    """ configure logging to stream output """
    handler = logging.StreamHandler(LOG_STREAM)
    log_format = LOG_FORMAT_DEFAULT
    log_level = logging.WARNING
    if options.quiet:
        handler = logging.NullHandler()
    elif options.debug:
        log_level = logging.DEBUG
        log_format = LOG_FORMAT_DEBUG
    elif options.verbose:
        log_level = logging.INFO

    root = logging.getLogger()
    root.setLevel(log_level)
    handler.formatter = ProxyTestLogFormatter(fmt=log_format, datefmt=LOG_DATE_FORMAT, style='{')
    root.handlers += [handler]


class Output:
    """ A namespace to keep all of the output logic in one place and easy to extend."""

    @staticmethod
    def runner_waiting(seconds: float):
        """ Runner is waiting for the repeat timeout. """
        LOGGER.info('Waiting for {:.2f}s before repeating. Use CTRL+C to exit.'.format(seconds))

    # noinspection PyUnusedLocal
    @classmethod
    def run_start(cls, runner: Runner, start_time: float):
        """ Runner is about to run a backend. """
        LOGGER.info('Starting {} requests using {}.'.format(runner.request_count, runner.backend.name))

    @classmethod
    def run_end(cls, runner: Runner, start_time: float):
        """ The backend finished processing the requests. """
        end_time = time.monotonic()
        duration = end_time - start_time
        duration_total = end_time - runner.start_time_all_runs
        failed_proxies = sorted((x.config.proxy_url for x in runner.context.requests if not x.status.succeeded))
        failed_count = len(failed_proxies)
        total_count = len(runner.context.requests)
        success_count = total_count - failed_count
        success_count_total = runner.ran_count - runner.failed_count
        params = dict(
                fail_count=failed_count,
                success_count=success_count,
                ran_count=total_count,
                fail_percent=(failed_count / total_count) * 100,
                success_percent=(success_count / total_count) * 100,
                duration=duration,
                duration_total=duration_total,
                fail_list=' '.join(failed_proxies),
                fail_count_total=runner.failed_count,
                success_count_total=success_count_total,
                fail_percent_total=(runner.failed_count / runner.ran_count) * 100,
                success_percent_total=(success_count_total / runner.ran_count) * 100,
        )

        # summary changes based on results
        summary = 'in {duration:.2f}s'.format(**params)
        if runner.failed_count:
            if runner.repeat_seconds:
                summary += ' ({success_percent_total:.0f}% success in {duration_total:.2f}s)'.format(**params)
            else:
                summary += ' ({success_percent_total:.0f}% success)'.format(**params)
        params['summary'] = summary

        # output different depending on whether this run succeeded
        if failed_count:
            LOGGER.info('{fail_count}/{ran_count} FAILED {summary}'.format(**params))
            for proxy in sorted(set(failed_proxies)):
                LOGGER.warning('FAILED: {}'.format(proxy))
        else:
            LOGGER.info('SUCCEEDED: all {ran_count} {summary}'.format(**params))

    @staticmethod
    def request_start(request: RequestInfo):
        """ Start of a single request. """
        data = request.get_placeholders()
        LOGGER.info('{proxy_url} ({idx}): Connecting to {url}'.format(**data))

    @staticmethod
    def request_end(request: RequestInfo, print_template: str = ''):
        """ End of a single request. """
        status = request.status
        data = request.get_placeholders()
        duration = status.finished - status.started

        # warn if failed
        if not status.succeeded:
            LOGGER.warning('{proxy_url} ({idx}): Error connecting to {url}: {error} '
                           '({duration:.2f}s)'.format(duration=duration, **data))
            return

        # log and optionally dump content on success
        LOGGER.info('{proxy_url} ({idx}): Success! Got {length} characters from {url} '
                    '({duration:.2f}s)'.format(length=len(status.result),
                                               duration=duration, **data))
        if print_template:
            print(print_template.format(
                    result_flat=' '.join(str(status.result).splitlines()),
                    duration=duration,
                    **data
            ))
