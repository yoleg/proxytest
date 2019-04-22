"""
Example backend that marks requests as started but not finished.

Used for testing.
"""
from proxytest import backend
from proxytest.request import ProxyTestContext


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-unfinished'

    def process(self, context: ProxyTestContext):
        for request in context.requests:
            request.start()
