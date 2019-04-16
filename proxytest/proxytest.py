#!/usr/bin/env python3
"""
This is a simple script to test if a proxy is working.

All it does is fetch a web page ("http://example.com/" by default) using the proxies.

Usage examples:
    python3 proxytest.py 1.2.3.4:8080-8082

    python3 proxytest.py "1.2.3.4:1234" "22.33.44.55:8080-8082" --verbose --url="https://exampledomain.com/example"
"""
import sys
from typing import List, Iterator
import argparse
import random
import logging
import requests

# The URL to get via the proxy (override with the --url command-line parameter)
DEFAULT_TEST_URL = 'http://example.com/'

# a random User Agent will be chosen from this list (copied from "howdoi" package)
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0',
    'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
    'Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
]

# the logger to use
LOGGER = logging.getLogger('proxytest')

# the requests session to use
SESSION = requests.Session()


def main():
    """ Run the program from the command line."""
    # process command-line arguments
    parser = argparse.ArgumentParser(description='Test if one or more HTTP proxies are working by requesting a webpage through each.')
    parser.add_argument('proxies', metavar='PROXYHOST:STARTPORT[-ENDPORT]', type=str, nargs='+',
                        help='The proxy host/ports to use. -ENDPORT is optional. Example: 1.2.3.4:8080 1.2.3.4:8080-8090')
    parser.add_argument('--url', '-u', dest='test_url', type=str, default=DEFAULT_TEST_URL, help='The URL of the webpage to get (default: "{}").'.format(DEFAULT_TEST_URL))
    parser.add_argument('--verbose', '-v', dest='verbose', action='store_true', help='Enable verbose output.')
    parser.add_argument('--print', '-p', dest='print', action='store_true', help='Dump the contents of each webpage to stdout.')
    options = parser.parse_args()

    # configure logging to stream output
    logging.basicConfig(level=logging.INFO if options.verbose else logging.WARNING)

    # convert port ranges such as '1.2.3.4:8080-8084', into full proxy_urls
    proxy_urls = []
    for proxy_string in options.proxies:
        for proxy_url in process_proxy_string(proxy_string):
            proxy_urls.append(proxy_url)

    # test each of the proxy URLs
    fail_count = process_urls(proxy_urls, test_url=options.test_url, output=options.print)

    # choose the exit code (0 on success)
    # noinspection PyShadowingNames
    exit_code = 2 if fail_count else 0
    return exit_code


def process_urls(proxy_urls: List[str], test_url: str, output=False):
    """ Fetch test_url for each of the proxy URLs, printing the request output if output is True. """
    LOGGER.info('Starting tests on {} proxies.'.format(len(proxy_urls)))
    fail_count = 0
    for proxy_url in proxy_urls:
        response = make_http_request(url=test_url, proxy_url=proxy_url)
        if response and output:
            print(response.text)
        if not response:
            fail_count += 1
    LOGGER.info('Done! {} proxies failed out of {} proxies tested'.format(fail_count, len(proxy_urls)))
    return fail_count


def make_http_request(url: str, proxy_url: str = None):
    """ Make a GET request to the URL, optionally using a proxy URL."""
    if not url:
        raise ValueError('No URL to test!')
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    proxies = None
    debug = '{} directly'.format(url)
    if proxy_url:
        # same proxy for both http and https URLs
        proxies = {
            'http': 'http://' + proxy_url,
            'https': 'https://' + proxy_url,
        }
        debug = '{} {}'.format(repr(url), 'via proxy: {} ...'.format(repr(proxy_url)))
    LOGGER.info('Connecting to {}'.format(debug))
    try:
        response = SESSION.get(url, headers=headers, proxies=proxies)
    except Exception as e:
        LOGGER.error('ERROR: could not get {}: {}'.format(debug, e))
        response = None
    else:
        LOGGER.info('Success! Got {:,} characters. Preview: {}'.format(len(response.text), repr(response.text[:50] + '...')))
    return response


def process_proxy_string(proxy_string: str) -> Iterator[str]:
    """ parse the proxies from command-line arguments, which are strings such as '1.2.3.4:8080-8084', generating single-port URLs """
    # separate host from ports
    try:
        host, ports = str(proxy_string).split(':')
    except ValueError:
        return fail('Invalid proxy: {}'.format(repr(proxy_string)))

    # find out if single port or range of ports
    try:
        start_port, end_port = ports.split('-', 1)
    except ValueError:
        start_port, end_port = ports, ports

    # make sure ports are integers
    try:
        start_port = int(start_port)
        end_port = int(end_port)
    except ValueError:
        return fail('Invalid proxy port(s): {}'.format(repr(proxy_string)))

    # yield individual 'HOST:PORT' strings
    for port in range(start_port, end_port + 1):
        yield host + ':' + str(port)


# noinspection PyShadowingNames
def fail(*args, exit_code=1):
    """ Print an error message and exit with exit code"""
    print('ERROR: ', *args)
    sys.exit(exit_code)


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
