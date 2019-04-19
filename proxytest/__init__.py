# exports
from .proxytest import *
from .version import __version__

# I want this __init__.py file here, but I also want proxytest.backends
# to be a namespace package. "pkgutil-style" seems to be the answer here!
# see https://packaging.python.org/guides/packaging-namespace-packages/#pkgutil-style-namespace-packages
# noinspection PyUnboundLocalVariable
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
