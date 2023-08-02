from functools import partial

from cacheback.jobs import FunctionJob
from cacheback.decorators import cacheback as cacheback_decorator


class UniversalDecoratorFunctionJob(FunctionJob):
    """
    Allow to wrap any function with cacheback decorator
    with the function name being the key prefix.
    """

    fetch_on_miss = True

    def key(self, fn, *args, **kwargs):
        return super().key(fn.__name__, *args, **kwargs)

    def hash(self, value):  # noqa: A003
        if not isinstance(value, list | tuple):
            value = [value]
        return ":".join(str(val) for val in value)

    def prepare_args(self, fn, *args):
        return (fn,) + args

    def fetch(self, func, *args, **kwargs):
        return func(*args, **kwargs)

    def should_stale_item_be_fetched_synchronously(self, *args, **kwargs):
        return True


cached = partial(cacheback_decorator, job_class=UniversalDecoratorFunctionJob)
