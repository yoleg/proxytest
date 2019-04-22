"""
Example backend that marks requests as done without doing anything.

Used for testing.
"""
from proxytest import backend
from proxytest.request import SessionInfo


class DummyBackend(backend.AbstractBackend):
    name = 'dummy'

    def process(self, info: SessionInfo):
        """ Process the requests one at a time, doing nothing.."""
        for request in info.requests:
            request.start()
            try:
                self.log.info('Doing nothing!')
            except Exception as e:
                # just an example, should never happen!
                request.finish(error=e)
            else:
                # should happen every time!
                request.finish(result='')
