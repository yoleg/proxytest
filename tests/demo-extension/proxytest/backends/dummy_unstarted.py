"""
Example backend that does absolutely nothing, not even marking requests as started or finished.

Used for testing.
"""
from proxytest import backend
from proxytest.request import SessionInfo


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-unstarted'

    def process(self, info: SessionInfo):
        pass
