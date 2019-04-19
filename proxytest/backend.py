"""
Self-registering backends.

The complexity is just for demonstration and totally unnecessary :).
"""
import abc
import contextlib
import importlib
import inspect
import logging
import pkgutil
from typing import Any, Callable, Iterable, Union

# type hints
from .request import SessionInfo

LOGGER = logging.getLogger('proxytest.backend')
BackendInterface = Callable[[SessionInfo], Any]
SUGGESTED_PACKAGES = []
""" List of uninstalled packages that would add backend options. """
REGISTRY = {}
"""
backend name to processor

:type: dict[str, BackendInterface]
"""


def reset_backends():
    REGISTRY.clear()
    SUGGESTED_PACKAGES.clear()


def find_backends():
    """ Automatically loads backends """
    # source: https://packaging.python.org/guides/creating-and-discovering-plugins/
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    import proxytest.backends
    ns_pkg = proxytest.backends
    module_iterator = pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")
    for finder, name, is_package in module_iterator:
        if '._' in name:
            continue
        with import_exception_manager(name):
            importlib.import_module(name)  # self-registers on import


@contextlib.contextmanager
def import_exception_manager(name):
    """ Processes backend-loading exceptions. """
    try:
        yield
    except MissingDependenciesError as e:
        LOGGER.debug('MissingDependenciesError: {}'.format(e.packages))
        SUGGESTED_PACKAGES.extend(e.packages)
    except NotSupportedError:
        LOGGER.debug('Unsupported backend: {}'.format(name))


# standardize logging

def get_logger(name: str) -> logging.Logger:
    """ Gets the appropriate logger for this backend name. """
    return logging.getLogger('proxytest.' + name)


class BaseBackendException(Exception):
    """ Base class for all custom exceptions defined here."""
    pass


# exceptions used by backends for self-reporting of unavailability

class NotSupportedError(BaseBackendException):
    """ Raised when importing a backend if it is not possible to run on this system. """


class MissingDependenciesError(NotSupportedError):
    """ Raised when importing a built-in backend if it requires missing packages. """

    def __init__(self, packages: Iterable[str] = None) -> None:
        self.packages = sorted(packages)
        super().__init__('missing packages: {}'.format(', '.join(self.packages)))


# Miscellaneous Exceptions

class ImplementationError(BaseBackendException):
    """ Raised if the backend does not conform to an interface. """
    pass


class AlreadyInRegistry(ImplementationError):
    """ Raised when the same backend key is registered twice"""
    pass


# backend auto-registration

# option 1: explicit registration
def register(name: str, processor: BackendInterface):
    """ Registers a backend."""
    if not name:
        raise ValueError('Missing backend name!')
    if not isinstance(name, str):
        raise TypeError('Backend name should be a string, got {}!'.format(type(name).__name__))
    if not callable(processor):
        raise TypeError('Processor should be a callable, got {}!'.format(type(name).__name__))
    if name in REGISTRY:
        raise AlreadyInRegistry(name)
    REGISTRY[name] = processor


# option 2: decorator
class BackendDecorator(object):
    """
    Use as an instance to pass in a name:

        >>> @BackendDecorator('my_backend')
        ... def my_backend_processor(requests, config):
        ...     pass
        ...


    Use as a class to use the function name as the backend name:
        >>> @BackendDecorator  # same as @BackendDecorator('my_backend')
        ... def my_backend(requests, config):
        ...     pass
        ...

    """

    def __new__(cls, name_or_fn: Union[str, BackendInterface]) -> Union[BackendInterface, 'BackendDecorator']:
        if callable(name_or_fn):
            register(name_or_fn.__name__, name_or_fn)
            return name_or_fn  # class used as decorator
        return super().__new__(cls)  # instance used as decorator

    def __init__(self, name: str):
        """
        Should only get here if an instance was used as a decorator.
        """
        self.name = name

    def __call__(self, f: BackendInterface):
        """
        Support an instance being used as a decorator.

        @BackendDecorator('my_backend')
        """
        register(self.name, f)
        return f  # unchanged


# option 3: abstract class that must be instantiated (problem: might forget!)
class AbstractBackendInstance(abc.ABC):
    name = None

    def __init__(self, name: str = None):
        name = name or getattr(self, 'name')
        self.name = name
        register(name, self)
        self.log = get_logger(name)

    @abc.abstractmethod
    def __call__(self, context: SessionInfo):
        pass


# option 4: metaclass (don't need to remember to instantiate)
class BackendMeta(abc.ABCMeta):
    """
    Makes the class itself a backend processor.

    The class's __new__/ __init__ must implement BackendInterface
    Backend name will be cls.name or derived from the class name
    """

    def __init__(cls, name, bases, dictionary):
        super().__init__(name, bases, dictionary)
        if inspect.isabstract(cls):
            return
        try:
            name = getattr(cls, 'name', None)
        except AttributeError:
            raise ImplementationError('"name" attribute is missing from {}!'.format(name))
        if not name:
            raise ImplementationError('"name" attribute is empty in {}!'.format(name))
        # noinspection PyTypeChecker
        register(name, cls)
        cls.name = name  # if callable name, replace it with a string


# option 5: abstract class that uses BackendMeta (clean and easy)
class AbstractBackend(metaclass=BackendMeta):
    name = None  # must be overridden
    """:type: str """

    def __init__(self, info: SessionInfo) -> None:
        super().__init__()
        self.log = logging.getLogger(self.name)
        self.process(info)

    @abc.abstractmethod
    def process(self, info: SessionInfo):
        pass
