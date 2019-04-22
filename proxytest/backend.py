"""
Self-registering, plugable backends.

The complexity here is just for demonstration and totally unnecessary :)

globals:
    * REGISTRY is a dict of a backend name to the backend processor.
    * SUGGESTED_PACKAGES is a list of uninstalled packages that
        might add more backend options if installed.

Backend processors are callables that accept a SessionInfo instance as a
positional argument. The callable does not need to return anything.

    def my_backend(info: SessionInfo):
        pass

Backends add their processors to the REGISTRY by using any of the tools provided here:

    1. calling register("name", processor)
    2. decorating the processor: @BackendDecorator or @BackendDecorator("name")
    3. subclassing and instantiating AbstractBackendInstance("name")
    4. using BackendMeta as a metaclass
    5. subclassing AbstractBackend - clean and easy!

When a backend module is imported, it can optionally raise the following exceptions:

    * NotSupportedError if not available on this system (e.g. async/ await syntax on Python 3.4)
    * MissingDependenciesError(list_of_suggested_packages) if missing a required package
        - this will update SUGGESTED_PACKAGES

find_backends() finds and imports all modules in the namespace package "proxytest.backends".
"""
import abc
import contextlib
import importlib
import inspect
import logging
import pkgutil
from typing import Any, Callable, Iterable, Union

from .request import SessionInfo  # for type hints

BackendInterface = Callable[[SessionInfo], Any]  # for type hints only

SUGGESTED_PACKAGES = []
""" List of uninstalled packages that would add backend options. """
REGISTRY = {}
"""
backend name to backend

:type: dict[str, BackendInterface]
"""

LOGGER = logging.getLogger('proxytest.backend')

_IMPORT_FLAG_NAME = '__proxytest_loaded__'


def reset_backends():
    REGISTRY.clear()
    SUGGESTED_PACKAGES.clear()


def find_backends():
    """
    Automatically loads backends from the proxytest.backends namespace package.

    This allows additional backends to be added from other packages.

    See:
        * https://packaging.python.org/guides/creating-and-discovering-plugins/
        * https://packaging.python.org/guides/packaging-namespace-packages/
    """
    import proxytest.backends
    namespace_package = proxytest.backends
    ns_path = namespace_package.__path__  # ['/path1/proxytest/backends/', '/path2/proxytest/backends/']
    ns_name = namespace_package.__name__ + "."  # 'proxytest.backends.'

    # source: https://packaging.python.org/guides/creating-and-discovering-plugins/
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    module_iterator = pkgutil.iter_modules(ns_path, ns_name)

    # iterate all modules and packages inside the namespace package paths
    for finder, name, is_package in module_iterator:
        if '._' in name:
            continue  # skip anything starting with an underscore

        with import_exception_manager(name):  # handle special exceptions
            module = importlib.import_module(name)
            if getattr(module, _IMPORT_FLAG_NAME, False):  # did this already
                # reload to call the registration methods again
                importlib.reload(module)
            else:
                setattr(module, _IMPORT_FLAG_NAME, True)  # first time - set the flag


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
        raise TypeError('name should be a string, got {}!'.format(type(name).__name__))
    if not callable(processor):
        raise TypeError('processor should be callable, got {}!'.format(type(name).__name__))
    if name in REGISTRY:
        raise AlreadyInRegistry(name)
    REGISTRY[name] = processor


# option 2: decorator, with and without arguments
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
        cls.name = name


# option 5: abstract class that uses BackendMeta (clean and easy!)
class AbstractBackend(metaclass=BackendMeta):
    name = None  # must be overridden
    """:type: str """

    def __init__(self, info: SessionInfo) -> None:
        super().__init__()
        self.log = get_logger(self.name)
        self.process(info)

    @abc.abstractmethod
    def process(self, info: SessionInfo):
        pass
