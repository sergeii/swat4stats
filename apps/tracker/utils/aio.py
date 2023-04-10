import logging
import asyncio
import functools
from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Callable, Coroutine
from uuid import uuid4

logger = logging.getLogger(__name__)


def with_semaphore(semaphore):
    def decorator(coroutine):
        @functools.wraps(coroutine)
        async def wrapper(*args, **kwargs):
            async with semaphore:
                return await coroutine(*args, **kwargs)
        return wrapper
    return decorator


def with_timeout(timeout, callback=None):
    def decorator(coroutine):
        @functools.wraps(coroutine)
        async def wrapper(*args, **kwargs):
            try:
                result = await asyncio.wait_for(coroutine(*args, **kwargs), timeout)
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


def run_many(tasks: list['Task']) -> None:
    async def runner():
        await asyncio.gather(*tasks)
    asyncio.run(runner())


class Task(ABC):

    def __init__(self, *,
                 callback: Callable | None = None,
                 id: Any | None = None):
        """
        Register a task with callback and optional id.
        If id is not specified, assign a random id to the task.
        """
        self.callback = callback
        self.id = id or uuid4()

    def __await__(self) -> Coroutine:
        return self.task()

    async def task(self) -> None:
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
        if not self.callback:
            return
        self.callback(self.id, result)

    async def fail(self, exc: Exception) -> None:
        if not self.callback:
            return
        self.callback(self.id, exc)
