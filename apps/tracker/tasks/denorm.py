import logging

from apps.tracker.models import Map, Profile, Server
from apps.utils.misc import iterate_queryset
from swat4stats.celery import Queue, app

__all__ = [
    "denorm_profile_names",
    "update_map_ratings",
    "update_server_ratings",
]

logger = logging.getLogger(__name__)


@app.task(name="denorm_profile_names", queue=Queue.default.value)
def denorm_profile_names(chunk_size: int = 1000) -> None:
    profiles_with_ids = Profile.objects.require_denorm_names().using("replica")
    for chunk in iterate_queryset(profiles_with_ids, fields=["pk"], chunk_size=chunk_size):
        profile_ids = [profile["pk"] for profile in chunk]
        Profile.objects.denorm_alias_names(*profile_ids)


@app.task(name="update_map_ratings", queue=Queue.default.value)
def update_map_ratings() -> None:
    Map.objects.update_ratings()


@app.task(name="update_server_ratings", queue=Queue.default.value)
def update_server_ratings() -> None:
    Server.objects.update_ratings()
