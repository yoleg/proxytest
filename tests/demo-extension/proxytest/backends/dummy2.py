"""
Example backend that marks requests as done without doing anything.

Used by for testing.
"""
from proxytest import backend
from proxytest.request import SessionInfo


class Dummy2Backend(backend.AbstractBackend):
    name = 'dummy2'

    def process(self, info: SessionInfo):
        """ Process the requests one at a time, doing nothing.."""
        for request in info.requests:
            request.start()
            request.finish(error=Exception('dummy2'))
