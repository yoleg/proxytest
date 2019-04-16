# proxytest

Simple command-line script to check if multiple proxies are up by fetching a webpage through each.

## Installation:

Requires Python 3.4 or above.

```
pip3 install proxytest
```

or

```
python3 -m pip install proxytest
```

## Usage examples:

```
proxytest 1.2.3.4:8080 1.2.3.4:8081

proxytest 1.2.3.4:8080-8081  # same as above

proxytest "http://user:pass@exampleproxy.com:3128" "111.222.333.444:8080-8082" "111.222.333.444:8085-8090" --verbose

proxytest "1.2.3.4:1234" --url="https://example.com"  --print

proxytest --help

python3 -m proxytest --version
```

## Exit codes:

* 0 - all proxy requests succeeded
* 1 - one or more proxy requests failed
* 2 - could not test proxies (e.g. due to input error or system error)

## Links:

Homepage: https://github.com/yoleg/proxytest

A list of free proxies that may be useful for testing (not verified or in any way associated with this project): https://hidemyna.me/en/proxy-list/
