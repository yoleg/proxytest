"""
Example backend that marks requests as done without doing anything.

Used for testing.
"""
from proxytest import backend
from proxytest.request import SessionInfo


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-success'

    def process(self, info: SessionInfo):
        for request in info.requests:
            request.start()
            request.finish(result='dummy success')
