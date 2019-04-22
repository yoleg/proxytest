# proxytest

[![Build Status](https://travis-ci.org/yoleg/proxytest.svg?branch=master)](https://travis-ci.org/yoleg/proxytest)
[![PyPI version](https://badge.fury.io/py/proxytest.svg)](https://badge.fury.io/py/proxytest)

Simple command-line script to check if multiple proxies are up by fetching a webpage through each (in parallel).

But the *main* purpose of proxytest is to be a Python **coding sample**, so it has way more features than it needs. :)

It's also an excuse for me to play with Travis, pypi, and namespace packages.

## Installation:

Requires Python 3.4 or above.

```
python3 -m pip install proxytest
```

## Examples:

```
proxytest http://1.2.3.4:8080 http://1.2.3.4:8081

proxytest 1.2.3.4:8080-8081  # same as above

proxytest -v -n 10 --timeout 1 "http://user:pass@exampleproxy.cofm:3128" "111.222.333.444:8080-8082" "111.222.333.444:8085-8090"

proxytest "1.2.3.4:1234" --url="https://example.com"  --print

proxytest --help

python3 -m proxytest --version
```

## Command-line Arguments:

```
$ proxytest --help
usage: proxytest [-h] [--version] [--agent AGENT]
                 [--backend {aiohttp,dummy,requests}] [--number NUMBER]
                 [--repeat SECONDS] [--timeout TIMEOUT] [--url TEST_URL]
                 [--workers WORKERS] [--print] [--format PRINT_FORMAT]
                 [--quiet] [--debug] [--verbose]
                 PROXYHOST:STARTPORT[-ENDPORT] [PROXYHOST:STARTPORT[-ENDPORT]
                 ...]

Test if one or more HTTP proxies are working by requesting a webpage through
each.

positional arguments:
  PROXYHOST:STARTPORT[-ENDPORT]
                        The proxy host/ports to use. -ENDPORT is optional.
                        Example: 1.2.3.4:8080 1.2.3.4:8080-8090. Use "none" to
                        call the webpage directly.

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --agent AGENT, -a AGENT
                        The user agent string to use. (default: random)
  --backend {aiohttp,dummy,requests}, -b {aiohttp,dummy,requests}
                        The backend to use. Choose from: aiohttp, dummy,
                        requests. (default: aiohttp)
  --number NUMBER, -n NUMBER
                        Number of times to test each proxy (default: 1)
  --repeat SECONDS, -r SECONDS
                        Continue running and repeat the test every X seconds
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout in seconds for each request. (default: 2)
  --url TEST_URL, -u TEST_URL
                        The URL of the webpage to get. (default:
                        'http://example.com/').
  --workers WORKERS, -j WORKERS
                        Max number of concurrent requests. (default:
                        unlimited)

output:
  --print, -p           Print each webpage to stdout on a successful fetch.
  --format PRINT_FORMAT, -f PRINT_FORMAT
                        The output format to use for --print. Placeholders:
                        config, end_callback, error, finished, headers, idx,
                        proxy_url, request, result, start_callback, started,
                        status, status_code, url. (default: 'Content from
                        {proxy_url} ({idx}): "{result_flat:.100}..."')
  --quiet, -q           Suppress logging. Overrides --debug and --verbose, but
                        --print will still work.
  --debug, -d           Enable debug logging to stderr. Overrides --verbose.
  --verbose, -v         Enable verbose logging to stderr.

```

## Backends:
 
Built-in backends:

* aiohttp - asyncio support (requires: `aiohttp`, Python >= 3.5.3)
* requests - useful for Python 3.4, supports HTTPS proxies (requires: `requests`)
* dummy - does not make any outgoing connections

Third-party extensions can add backends by using the `proxytest.backends` [namespace package](https://packaging.python.org/guides/packaging-namespace-packages/). See the `tests/` directory for an example.

If a backend's requirements have not been met, the `--help` description for the `--backend` option will show a list of recommended packages to install that would enable more backends.

## Output:

No output on success unless verbose or debug mode enabled.

## Exit codes:

* 0 - all proxy requests succeeded
* 1 - one or more proxy requests failed
* 2 - could not test proxies (e.g. due to input error or system error)

## History:

A client needed a script to periodically check the outgoing connections on a dozen or so private proxies. A search for "proxy test" in pypi found nothing relevant.
  
Normally, I would have just written a simple wrapper for an HTTP client with proxy support (such as httpie).

But instead, I grabbed the ~~excuse~~ opportunity to write a ~~coding sample~~ open source package that ~~might have a tiny chance of being useful~~ might be useful to someone else.

## Links:

Homepage: https://github.com/yoleg/proxytest

A list of free proxies that may be useful for testing (not verified or in any way associated with this project): https://hidemyna.me/en/proxy-list/
