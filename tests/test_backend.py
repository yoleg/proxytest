#!/usr/bin/env python3
""" Tests for proxytest. """
import unittest

from proxytest import backend, SessionInfo


class ProxyBackendImportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        assert not backend.REGISTRY
        assert not backend.SUGGESTED_PACKAGES
        self.addCleanup(backend.reset_backends)

    def _assert_registered(self, name: str, fn: callable):
        self.assertIn(name, backend.REGISTRY)
        self.assertIs(backend.REGISTRY[name], fn)

    def test_find_backends(self):
        backend.find_backends()
        self.assertNotIn('unavailable', backend.REGISTRY)
        self.assertIn('dummy', backend.REGISTRY)

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
