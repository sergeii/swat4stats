import logging
import asyncio
import functools
from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Callable, Coroutine
from uuid import uuid4

logger = logging.getLogger(__name__)


def with_timeout(timeout, callback=None):
    def decorator(coro):
        @functools.wraps(coro)
        async def wrapper(*args, **kwargs):
            try:
                result = await asyncio.wait_for(coro(*args, **kwargs), timeout)
            except asyncio.TimeoutError as exc:
                if isinstance(callback, Exception):
                    raise callback from exc
                elif callable(callback):
                    callback(args, kwargs, exc)
                else:
                    raise
            else:
                return result
        return wrapper
    return decorator


async def run(coro: Coroutine, semaphore: asyncio.Semaphore | None) -> None:
    if semaphore is None:
        await coro
    else:
        async with semaphore:
            logger.debug('acquired semaphore %s for %s', semaphore, coro)
            await coro


def run_many(tasks: list['Task'], concurrency: int | None = None) -> None:
    async def runner():
        semaphore = asyncio.Semaphore(concurrency) if concurrency else None
        runnables = (run(task.execute(), semaphore=semaphore) for task in tasks)
        await asyncio.gather(*runnables)
    asyncio.run(runner())


class Task(ABC):

    def __init__(self, *,
                 callback: Callable | None = None,
                 id: Any | None = None):
        """
        Register a task with callback and optional id.
        If id is not specified, assign a random id to the task.
        """
        self._callback = callback
        self._id = id or uuid4()

    async def execute(self) -> None:
        try:
            result = await self.start()
        except Exception as exc:
            logger.info('failed to complete task %s due to %s: %s', self, type(exc).__name__, exc)
            await self.fail(exc)
        else:
            logger.debug('completed task %s', self)
            await self.complete(result)

    @abstractmethod
    async def start(self) -> None:
        ...

    async def complete(self, result: Any) -> None:
        if not self._callback:
            return
        self._callback(self._id, result)

    async def fail(self, exc: Exception) -> None:
        if not self._callback:
            return
        self._callback(self._id, exc)
