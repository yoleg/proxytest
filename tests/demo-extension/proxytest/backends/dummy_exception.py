"""
Example backend that marks requests as done without doing anything.

Used for testing.
"""
from proxytest import backend
from proxytest.context import ProxyTestContext


class FakeException(Exception):
    pass


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-exception'

    def process(self, context: ProxyTestContext):
        raise FakeException('Fake exception')
