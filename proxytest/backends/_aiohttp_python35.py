"""
The aiohttp backend (request processor function).

Uses asyncio for concurrency.

Requires "aiohttp" package. Useful for Python 3.5 or above.
"""
import asyncio

from proxytest import backend
from proxytest.request import RequestInfo, SessionInfo

try:
    # noinspection PyPackageRequirements
    import aiohttp
except ImportError:
    raise backend.MissingDependenciesError(['aiohttp'])

_BACKEND_NAME = 'aiohttp'

LOGGER = backend.get_logger(_BACKEND_NAME)


@backend.BackendDecorator(_BACKEND_NAME)
def process_requests(context: SessionInfo = None):
    """ Process the requests in parallel using aiohttp."""
    context = context or SessionInfo()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_process_requests_coroutine(context))


async def _process_requests_coroutine(context: SessionInfo = None):
    # noinspection PyBroadException
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=context.timeout)) as session:
            batch_size = context.max_workers or len(context.requests)
            for i in range(0, len(context.requests), batch_size):
                tasks = []
                for request in context.requests[i: i + batch_size]:
                    task = asyncio.ensure_future(_process_request(session=session, request=request))
                    tasks.append(task)
                await asyncio.gather(*tasks)
    except Exception:
        LOGGER.exception('Exception processing requests!')


_warned = False


def _warn_once_https_proxy():
    global _warned
    if not _warned:
        LOGGER.warning('aiohttp backend does not support https proxies (as of aiohttp 3.5.4). Try the "requests" backend.')
        _warned = True


async def _process_request(session: aiohttp.ClientSession, request: RequestInfo):
    if request.config.proxy_url and request.config.proxy_url.startswith('https://'):
        _warn_once_https_proxy()
    request.start()
    try:
        async with session.get(request.config.url, proxy=request.config.proxy_url, headers=request.config.headers) as response:
            response.raise_for_status()
            text = await response.text()
    except Exception as e:
        request.finish(error=e)
    else:
        request.finish(result=text)