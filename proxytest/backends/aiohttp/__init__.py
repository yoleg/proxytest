"""
A wrapper for the aiohttp backend that allows cleaner handling of <Python3.5
"""
import sys

from proxytest import backend

try:
    # this implementation causes a SyntaxError in Python3.4 and earlier,
    # so we need to keep it in a separate file
    from ._aiohttp_python35 import *
except SyntaxError:

    if sys.version_info < (3, 5):  # syntax error in earlier versions of Python due to async/ await syntax
        raise backend.NotSupportedError()

    raise  # some other syntax error - don't ignore!
