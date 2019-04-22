"""
Example backend that marks requests as done without doing anything.

Used for testing.
"""
from proxytest import backend
from proxytest.request import ProxyTestContext


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-success'

    def process(self, context: ProxyTestContext):
        for request in context.requests:
            request.start()
            request.finish(result='dummy success')
