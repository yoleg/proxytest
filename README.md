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
proxytest 1.2.3.4:8080-8082

proxytest "1.2.3.4:1234" "111.222.333.444:8080-8082" "111.222.333.444:8085-8090" --verbose

proxytest "1.2.3.4:1234" --url="https://example.com"  --print

proxytest --help
```

## Exit codes:

* 1 - invalid input
* 2 - at least one proxy failed

## Links:

https://github.com/yoleg/proxytest
