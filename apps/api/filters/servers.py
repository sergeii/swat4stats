from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.api.serializers import ServerFilterSerializer
from apps.tracker.models import Server


class ServerFilterBackend(DjangoFilterBackend):
    serializer_class = ServerFilterSerializer

    def filter_queryset(
        self, request: Request, objects: QuerySet[Server], view: GenericViewSet
    ) -> list[Server]:
        objects = super().filter_queryset(request, objects, view)

        filter_serializer = self.serializer_class(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        for param, value in filter_serializer.validated_data.items():
            # default value
            if value is None:
                continue

            filter_method = getattr(self, f"filter_{param}")
            filtered_objects = (filter_method(obj, value) for obj in objects)
            objects = [obj for obj in filtered_objects if obj]

        return objects

    def filter_full(self, obj: Server, value: bool) -> Server | None:  # noqa: FBT001
        if (obj.status["numplayers"] == obj.status["maxplayers"]) == value:
            return obj
        return None

    def filter_empty(self, obj: Server, value: bool) -> Server | None:  # noqa: FBT001
        if (obj.status["numplayers"] == 0) == value:
            return obj
        return None

    def filter_passworded(self, obj: Server, value: bool) -> Server | None:  # noqa: FBT001
        if obj.status["password"] == value:
            return obj
        return None

    def filter_gamename(self, obj: Server, value: str) -> Server | None:
        if obj.status["gamevariant"] == value:
            return obj
        return None

    def filter_gamever(self, obj: Server, value: str) -> Server | None:
        if obj.status["gamever"] == value:
            return obj
        return None

    def filter_gametype(self, obj: Server, value: str) -> Server | None:
        if obj.status["gametype"] == value:
            return obj
        return None

    def filter_mapname(self, obj: Server, value: str) -> Server | None:
        if obj.status["mapname"] == value:
            return obj
        return None
