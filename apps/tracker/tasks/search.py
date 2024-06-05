import logging
from enum import StrEnum

from django.db.models import Model as DjangoModel

from apps.tracker.models import Alias, Profile, Server
from apps.utils.misc import iterate_queryset
from swat4stats.celery import Queue, app

__all__ = [
    "update_search_vector",
    "update_search_vector_for_model",
    "SearchVectorModel",
]

logger = logging.getLogger(__name__)


class SearchVectorModel(StrEnum):
    profile = "profile"
    alias = "alias"
    server = "server"

    def to_model(self) -> type[Profile | Alias | Server]:
        match self:
            case SearchVectorModel.profile:
                return Profile
            case SearchVectorModel.alias:
                return Alias
            case SearchVectorModel.server:
                return Server
            case _:
                err_msg = f"Unknown model {self}"
                raise ValueError(err_msg)

    @classmethod
    def from_model(cls, model: type[DjangoModel]) -> "SearchVectorModel":
        mapping: dict[type[DjangoModel], SearchVectorModel] = {
            Profile: cls.profile,
            Alias: cls.alias,
            Server: cls.server,
        }

        if svm := mapping.get(model):
            return svm

        err_msg = f"Unknown model {model}"
        raise ValueError(err_msg)


@app.task(name="update_search_vector", queue=Queue.default.value)
def update_search_vector() -> None:
    for model in [Profile, Alias, Server]:
        svm = SearchVectorModel.from_model(model)
        logger.info("firing search vector update task for %s (%s)", svm, model.__name__)
        update_search_vector_for_model.delay(svm)


@app.task(queue=Queue.default.value)
def update_search_vector_for_model(model_alias: str, chunk_size: int = 1000) -> None:
    model_class = SearchVectorModel[model_alias].to_model()
    logger.info("updating search vector for %s", model_class.__name__)

    items_with_ids = model_class.objects.require_search_update().using("replica")

    for chunk in iterate_queryset(items_with_ids, fields=["pk"], chunk_size=chunk_size):
        model_class.objects.update_search_vector(*(item["pk"] for item in chunk))
