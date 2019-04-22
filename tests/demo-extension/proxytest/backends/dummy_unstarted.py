"""
Example backend that does absolutely nothing, not even marking requests as started or finished.

Used for testing.
"""
from proxytest import backend
from proxytest.request import ProxyTestContext


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-unstarted'

    def process(self, context: ProxyTestContext):
        pass
