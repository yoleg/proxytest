"""
Example backend that marks requests as failed without actually processing them.

Used for testing/ demonstration.
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
        # warn the user that this is not a good backend to use
        suggestions = backend.get_recommendation(excluded=[self.name])
        self.log.warning('The "{}" backend is for demonstration only. {}'
                         .format(self.name, suggestions))

        # simulate an error for each request
        for request in context.requests:
            request.start()
            pass  # do nothing
            request.finish(error=DummyError('DUMMY: nothing done!'))
