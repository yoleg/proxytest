"""
Example backend that marks requests as done without doing anything.

Used for testing.
"""
from proxytest import backend
from proxytest.context import ProxyTestContext


class DummyBackend(backend.AbstractBackend):
    """ Example backend that uses does nothing. """
    name = 'dummy'

    def process(self, context: ProxyTestContext):
        """ Process the requests one at a time, doing nothing.."""
        for request in context.requests:
            request.start()
            try:
                self.log.info('Doing nothing!')
            except Exception as e:
                # just an example, should never happen!
                request.finish(error=e)
            else:
                # should happen every time!
                request.finish(result='')
