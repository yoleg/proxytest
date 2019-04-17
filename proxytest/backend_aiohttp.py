"""
The aiohttp backend (request processor function).

Uses asyncio for concurrency.

Requires "aiohttp" package. Useful for Python 3.5 or above.
"""
import asyncio
import logging
from typing import List
import aiohttp

from ._info import RequestInfo, SessionConfig

LOGGER = logging.getLogger('proxytest.aiohttp')


def process_requests(request_infos: List[RequestInfo], config: SessionConfig = None):
    """ Process the requests in parallel using aiohttp."""
    config = config or SessionConfig()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_process_requests_coroutine(request_infos, config=config))


async def _process_requests_coroutine(request_infos: List[RequestInfo], config: SessionConfig = None):
    # noinspection PyBroadException
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout)) as session:
            batch_size = config.max_workers or len(request_infos)
            for i in range(0, len(request_infos), batch_size):
                tasks = []
                for request in request_infos[i: i + batch_size]:
                    task = asyncio.ensure_future(_process_request(session=session, request=request))
                    tasks.append(task)
                await asyncio.gather(*tasks)
    except Exception:
        LOGGER.exception('Exception processing requests!')


async def _process_request(session: aiohttp.ClientSession, request: RequestInfo):
    request.set_started()
    try:
        async with session.get(request.url, proxy=request.proxy_url, headers=request.headers) as response:
            response.raise_for_status()
            text = await response.text()
    except Exception as e:
        request.set_finished(error=str(e))
    else:
        request.set_finished(result=text)
