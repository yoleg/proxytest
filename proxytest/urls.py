""" Expands command-line proxy URLs into full, valid proxy URLs"""
from urllib.parse import urlparse

from typing import Iterator, Tuple


def expand_proxy_url(proxy_url: str, default_port: int = 8080) -> Iterator[str]:
    """ parse the proxies from command-line arguments, which are strings such as 'user:pass@1.2.3.4:8080-8084', generating single-port URLs """
    if not proxy_url:
        raise ValueError('proxy_url is required')

    if not proxy_url.startswith('http'):
        proxy_url = 'http://' + proxy_url
    parsed = urlparse(proxy_url)
    if (parsed.path and parsed.path != '/') or parsed.params or parsed.query or parsed.fragment:
        raise ValueError('Proxy path cannot have anything after the port or port range.')

    netloc = parsed.netloc  # can't use parsed.port because port range would make it invalid
    auth_prefix, host, start_port, end_port = _split_netloc(netloc)

    # handle missing start and/ or end port
    start_port = start_port or default_port
    end_port = end_port or start_port

    # yield valid proxy strings
    for port in range(start_port, end_port + 1):
        yield (parsed.scheme) + '://' + auth_prefix + host + ':' + str(port)


def _split_netloc(netloc: str) -> Tuple[str, str, int, int]:
    try:
        # separate user/ password from host/ port if it exists
        user_pass, host_port = str(netloc).split('@', 1)
        auth_prefix = user_pass + '@'
    except ValueError:
        user_pass, host_port = '', netloc
        auth_prefix = ''
    try:
        # separate hosts from ports if they exist
        host, ports = str(host_port).split(':', 1)
    except ValueError:
        host, ports = host_port, ''
    try:
        # handle range of ports
        start_port, end_port = ports.split('-', 1)
    except ValueError:
        start_port, end_port = ports, ports
    try:
        # make sure ports are integers (or empty)
        start_port = int(start_port or 0)
        end_port = int(end_port or 0)
    except ValueError:
        raise ValueError('Invalid port(s) {!r} {!r}'.format(start_port, end_port))
    return auth_prefix, host, start_port, end_port
