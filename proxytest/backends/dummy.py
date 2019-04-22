"""
Example backend that marks requests as done without doing anything.

Used for testing.
"""
from proxytest import backend
from proxytest.context import ProxyTestContext


class DummyError(Exception):
    """ Dummy Exception. """
    pass


class DummyBackend(backend.AbstractBackend):
    """ Example backend that uses does nothing. """
    name = 'dummy'

    def process(self, context: ProxyTestContext):
        """ Process the requests one at a time, doing nothing.."""
        for request in context.requests:
            request.start()
            self.log.warning('DUMMY: doing nothing!')
            request.finish(error=DummyError('DUMMY: nothing tested!'))
