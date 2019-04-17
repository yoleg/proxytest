# proxytest

[![Build Status](https://travis-ci.org/yoleg/proxytest.svg?branch=master)](https://travis-ci.org/yoleg/proxytest)
[![PyPI version](https://badge.fury.io/py/proxytest.svg)](https://badge.fury.io/py/proxytest)

Simple command-line script to check if multiple proxies are up by fetching a webpage through each (in parallel).

The only advantage of this tool over a commandline HTTP client (such as httpie) is that it provides an **easy way to check multiple proxies at once**.

But the *main* purpose of proxytest is to be a **Python coding sample**, so it has more features than it really needs. :)

## Installation:

Requires Python 3.4 or above.

```
python3 -m pip install proxytest
```

## Examples:

```
proxytest http://1.2.3.4:8080 http://1.2.3.4:8081

proxytest 1.2.3.4:8080-8081  # same as above

proxytest -v -n 10 --timeout 1 "http://user:pass@exampleproxy.com:3128" "111.222.333.444:8080-8082" "111.222.333.444:8085-8090"

proxytest "1.2.3.4:1234" --url="https://example.com"  --print

proxytest --help

python3 -m proxytest --version
```

## Command-line Arguments:

```
$ proxytest --help
usage: proxytest [-h] [--version] [--agent AGENT]
                 [--backend {aiohttp,requests}] [--number NUMBER]
                 [--timeout TIMEOUT] [--url TEST_URL] [--workers WORKERS]
                 [--print] [--format PRINT_FORMAT] [--quiet] [--debug]
                 [--verbose]
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
  --backend {aiohttp,requests}, -b {aiohttp,requests}
                        The backend to use. Choose from: aiohttp, requests.
                        (default: aiohttp)
  --number NUMBER, -n NUMBER
                        Number of times to test each proxy (default: 1)
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
                        duration, end_callback, error, finished, headers,
                        name, proxy_url, result, result_flat, start_callback,
                        started, url. (default: 'Content from {name}:
                        "{result_flat:.100}..."')
  --quiet, -q           Suppress logging. Overrides --debug and --verbose, but
                        --print will still work.
  --debug, -d           Enable debug logging to stderr. Overrides --verbose.
  --verbose, -v         Enable verbose logging to stderr.
```

## Backends:

* aiohttp (default) - asyncio support (requires Python 3.5.3 or above)
* requests - useful for Python 3.4, supports HTTPS proxies

## Output:

No output on success unless verbose or debug mode enabled.

## Exit codes:

* 0 - all proxy requests succeeded
* 1 - one or more proxy requests failed
* 2 - could not test proxies (e.g. due to input error or system error)

## Links:

Homepage: https://github.com/yoleg/proxytest

A list of free proxies that may be useful for testing (not verified or in any way associated with this project): https://hidemyna.me/en/proxy-list/
