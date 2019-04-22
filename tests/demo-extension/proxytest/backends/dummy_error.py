"""
Example backend that marks requests as failed without doing anything.

Used for testing.
"""
from proxytest import backend
from proxytest.request import SessionInfo


class DummyError(Exception):
    pass


class DummyBackend(backend.AbstractBackend):
    name = 'dummy-error'

    def process(self, info: SessionInfo):
        for request in info.requests:
            request.start()
            request.finish(error=DummyError('dummy error'))
