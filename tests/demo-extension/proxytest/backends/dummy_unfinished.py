"""
Example backend that marks requests as started but not finished.

Used for testing.
"""
from proxytest import backend
from proxytest.request import SessionInfo


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-unfinished'

    def process(self, info: SessionInfo):
        for request in info.requests:
            request.start()
