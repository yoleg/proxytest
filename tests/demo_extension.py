#!/usr/bin/env python3
"""
Tools for unit tests to activate and deactivate "demo-extension"
"""
import importlib
import sys
from pathlib import Path
from typing import List

demo_extension_path = str(Path(__file__).parent / 'demo-extension')


def get_namespace_package_path() -> List[str]:
    # keep in own namespace
    import proxytest.backends
    return proxytest.backends.__path__


def reload_namespace_package():
    """ Required to update proxytest.backends.__path__ after modifying sys.path """
    # keep in own namespace
    import proxytest
    importlib.reload(proxytest)


def activate_demo_extension():
    if demo_extension_path not in sys.path:
        sys.path.append(demo_extension_path)
        reload_namespace_package()  # required after modifying path
    # verify namespace package updated correctly
    ns_path = get_namespace_package_path()
    if len(ns_path) < 2:
        raise Exception('Namespace path less than 2 after adding demo extension: {}'.format(ns_path))


def deactivate_demo_extension():
    try:
        sys.path.remove(demo_extension_path)
    except ValueError:
        return
    reload_namespace_package()  # required after modifying path
