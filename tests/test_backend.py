#!/usr/bin/env python3
""" Tests for proxytest pluggable backends. """
import importlib
import sys
import unittest
from pathlib import Path
from typing import List

from proxytest import backend, SessionInfo

demo_extension_path = str(Path(__file__).parent / 'demo-extension')


def _get_namespace_package_path() -> List[str]:
    import proxytest.backends
    return proxytest.backends.__path__


def _reload_namespace_package():
    """ Required to update proxytest.backends.__path__ after modifying sys.path """
    # keep in own namespace
    import proxytest
    importlib.reload(proxytest)


class ProxyBackendImportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        assert not backend.REGISTRY
        assert not backend.SUGGESTED_PACKAGES
        self.addCleanup(backend.reset_backends)
        self._old_path = sys.path

    def _assert_registered(self, name: str, fn: callable):
        self.assertIn(name, backend.REGISTRY)
        self.assertIs(backend.REGISTRY[name], fn)

    def test_find_backends(self):
        backend.find_backends()
        self.assertIn('dummy', backend.REGISTRY)

        # clearable
        backend.reset_backends()
        self.assertNotIn('dummy', backend.REGISTRY)

        # repeatable
        backend.find_backends()
        self.assertIn('dummy', backend.REGISTRY)

    def test_find_backends_namespace_path(self):
        def _restore_path():
            sys.path.remove(demo_extension_path)
            _reload_namespace_package()  # required after modifying path

        if demo_extension_path not in sys.path:
            sys.path.append(demo_extension_path)
            _reload_namespace_package()  # required after modifying path
            self.addCleanup(_restore_path)

        # verify namespace package updated correctly
        ns_path = _get_namespace_package_path()
        self.assertGreaterEqual(len(ns_path), 2)

        # find_backends should now load backends from both demo_extension_path and the main proxytest module
        backend.find_backends()
        self.assertNotIn('unavailable', backend.REGISTRY)
        self.assertIn('dummy', backend.REGISTRY)
        self.assertIn('dummy2', backend.REGISTRY)

    def test_import_exception_manager(self):
        with backend.import_exception_manager('a'):
            raise backend.MissingDependenciesError(['b', 'c'])
        self.assertNotIn('a', backend.SUGGESTED_PACKAGES)
        self.assertIn('b', backend.SUGGESTED_PACKAGES)
        self.assertIn('c', backend.SUGGESTED_PACKAGES)

    def test_register(self):
        def demo_processor(_):
            pass

        def demo_processor2(_):
            pass

        backend.register('abc', demo_processor)
        self._assert_registered('abc', demo_processor)
        backend.register('xyz', demo_processor)
        self._assert_registered('xyz', demo_processor)

        with self.assertRaises(backend.AlreadyInRegistry):
            backend.register('abc', demo_processor2)

    def test_BackendDecorator(self):
        @backend.BackendDecorator
        def backend_unnamed(_):
            return 'a'

        @backend.BackendDecorator('name_override')
        def backend_named(_):
            return 'b'

        self._assert_registered('backend_unnamed', backend_unnamed)
        self._assert_registered('name_override', backend_named)

    def test_AbstractBackendInstance(self):
        class A(backend.AbstractBackendInstance):

            def __init__(self, name: str = None, extra=None):
                super().__init__(name)
                self.extra = extra

            def __call__(self, context: SessionInfo):
                pass

        class B(backend.AbstractBackendInstance):
            name = 'class_var'

            def __call__(self, context: SessionInfo):
                pass

        self.assertNotIn('class_var', backend.REGISTRY)

        a1 = A('one', extra=1)
        self._assert_registered('one', a1)
        self.assertIs(a1.extra, 1)

        with self.assertRaises(ValueError):
            A()

        a2 = A('two', extra=2)
        self._assert_registered('two', a2)
        self.assertIs(a2.extra, 2)
        self.assertNotEqual(a1, a2)

        self.assertNotIn('class_var', backend.REGISTRY)
        b = B()
        self._assert_registered('class_var', b)

    # noinspection PyPep8Naming
    def test_AbstractBackend(self):
        with self.assertRaises(backend.ImplementationError):
            class _(backend.AbstractBackend):
                def process(self, info: SessionInfo):
                    pass

        self.assertFalse(backend.REGISTRY)

        class B(backend.AbstractBackend):
            name = 'name_one'

            def process(self, info: SessionInfo):
                pass

        self._assert_registered('name_one', B)


if __name__ == '__main__':
    unittest.main()
