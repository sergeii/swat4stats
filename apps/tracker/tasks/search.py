import logging

from apps.tracker.models import Profile, Alias
from apps.utils.misc import iterate_queryset
from swat4stats.celery import app, Queue


__all__ = [
    "update_search_vector",
    "update_search_vector_for_profiles",
    "update_search_vector_for_aliases",
]

logger = logging.getLogger(__name__)


@app.task(name="update_search_vector", queue=Queue.default.value)
def update_search_vector() -> None:
    update_search_vector_for_profiles.delay()
    update_search_vector_for_aliases.delay()


@app.task(queue=Queue.default.value)
def update_search_vector_for_profiles(chunk_size: int = 1000) -> None:
    profiles_with_ids = Profile.objects.require_search_update().using("replica")
    for chunk in iterate_queryset(profiles_with_ids, fields=["pk"], chunk_size=chunk_size):
        profile_ids = [profile["pk"] for profile in chunk]
        Profile.objects.update_search_vector(*profile_ids)


@app.task(queue=Queue.default.value)
def update_search_vector_for_aliases(chunk_size: int = 1000) -> None:
    aliases_with_ids = Alias.objects.require_search_update().using("replica")
    for chunk in iterate_queryset(aliases_with_ids, fields=["pk"], chunk_size=chunk_size):
        alias_ids = [profile["pk"] for profile in chunk]
        Alias.objects.update_search_vector(*alias_ids)
