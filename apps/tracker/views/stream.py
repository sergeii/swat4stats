import logging
from typing import Any

from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import generic

from apps.tracker import schema
from apps.tracker.models import Server
from apps.tracker.tasks import process_game_data
from apps.tracker.views.api import APIError, APIResponse, require_julia_schema

logger = logging.getLogger(__name__)

schema_error_message = _(
    "Unable to process the round data due to version mismatch\n"
    "Are you using the latest mod version?\n"
    "If not, please install the latest version from swat4stats.com/install"
)


@method_decorator(require_julia_schema(schema.game_schema, schema_error_message), name="post")
class DataStreamView(generic.View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return HttpResponseRedirect("/")

    def post(self, request: HttpRequest, game_data: dict[str, Any]) -> HttpResponse:
        try:
            return self.handle(request, game_data)
        except APIError as exc:
            return APIResponse.from_error(exc.message)

    @transaction.atomic
    def handle(self, request: HttpRequest, game_data: dict[str, Any]) -> HttpResponse:
        server = self._get_or_create_server(
            ip=request.META["REAL_REMOTE_ADDR"], port=game_data["port"]
        )
        received_at = timezone.now()

        logger.info(
            "process data for game %s from %s at %s", game_data["tag"], server.address, received_at
        )
        transaction.on_commit(
            lambda: process_game_data.delay(
                server_id=server.pk, data=game_data, data_received_ts=received_at.timestamp()
            )
        )

        self._update_server_mod_version(server, game_data["version"])

        return APIResponse.from_success()

    def _get_or_create_server(self, ip: str, port: int) -> Server:
        """
        Attempt to find an existing server for the client IP
        and the port reported in the request data.

        If none found, create a new instance.

        Raise APIError if the found server is disabled
        """
        logger.debug("looking for server with ip %s port %s", ip, port)

        attrs = {"ip": ip, "port": port}

        try:
            server = Server.objects.get(**attrs)
            logger.debug("obtained server %s for %s", server.pk, server.address)
        except Server.DoesNotExist:
            server = Server.objects.create_server(**attrs)
            logger.debug("created server %s for %s", server.pk, server.address)

        if not server.enabled:
            logger.debug("server %s (%s) is disabled", server.pk, server.address)
            raise APIError(_("The server is not registered."))

        return server

    def _update_server_mod_version(self, server: Server, version: str) -> None:
        """
        Update the server mod version if it has changed
        """
        if server.version != version:
            logger.info(
                "updating mod version for %s (%d) from %s to %s",
                server.address,
                server.pk,
                server.version,
                version,
            )
            server.version = version
            server.save(update_fields=["version"])
        else:
            logger.debug(
                "mod version for %s (%d) is up to date (%s)",
                server.address,
                server.pk,
                server.version,
            )
