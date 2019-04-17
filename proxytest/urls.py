""" Expands command-line proxy URLs into full, valid proxy URLs"""
from urllib.parse import urlparse

from typing import Iterator


def expand_proxy_url(proxy_url: str, default_port: int='8080') -> Iterator[str]:
    """ parse the proxies from command-line arguments, which are strings such as 'user:pass@1.2.3.4:8080-8084', generating single-port URLs """
    if not proxy_url:
        raise ValueError('proxy_url is required')

    if not proxy_url.startswith('http'):
        proxy_url = 'http://' + proxy_url
    parsed = urlparse(proxy_url)
    if (parsed.path and parsed.path != '/') or parsed.params or parsed.query or parsed.fragment:
        raise ValueError('Proxy path cannot have anything after the port or port range.')

    netloc = parsed.netloc  # can't use parsed.port because port range would make it invalid
    try:
        # separate user/ password from host/ port if it exists
        user_pass, host_port = str(netloc).split('@', 1)
    except ValueError:
        user_pass = ''
        host_port = netloc
    try:
        # separate hosts from ports if they exist
        host, ports = str(host_port).rsplit(':', -1)
    except ValueError:
        host = host_port
        ports = str(default_port)
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
        raise ValueError('Invalid port(s)')

    # yield individual 'HOST:PORT' strings
    for port in range(start_port, end_port + 1):
        yield (parsed.scheme) + '://' + (user_pass and user_pass + '@') + host + ':' + str(port)
