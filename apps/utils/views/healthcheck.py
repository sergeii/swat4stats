import logging
import os
from enum import StrEnum, auto

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


def status(_: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "version": os.environ.get("GIT_RELEASE_VER"),
            "commit": os.environ.get("GIT_RELEASE_SHA"),
        }
    )


class Healthcheck(StrEnum):
    database = auto()
    redis = auto()


class HealthcheckStatus(StrEnum):
    ok = auto()
    failure = auto()


class HealthcheckView(View):
    def get(self, _: HttpRequest) -> JsonResponse:
        checks: dict[Healthcheck, HealthcheckStatus] = {
            Healthcheck.database: self._check_database(),
            Healthcheck.redis: self._check_redis(),
        }
        ok = all(s is HealthcheckStatus.ok for s in checks.values())
        return JsonResponse(
            {check.value: status.value for check, status in checks.items()},
            status=200 if ok else 400,
        )

    def _check_database(self) -> HealthcheckStatus:
        try:
            is_master = self._check_connected_to_master()
        except Exception:
            logger.exception("failed to check database")
            return HealthcheckStatus.failure

        match is_master:
            case True:
                return HealthcheckStatus.ok
            case _:
                return HealthcheckStatus.failure

    def _check_connected_to_master(self) -> bool:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_is_in_recovery();")
            row = cur.fetchone()
            return not row[0]

    def _check_redis(self) -> HealthcheckStatus:
        try:
            self._check_redis_rw()
        except Exception:
            logger.exception("failed to check redis")
            return HealthcheckStatus.failure
        return HealthcheckStatus.ok

    def _check_redis_rw(self) -> None:
        redis = cache.client.get_client()
        redis.set("_healthcheck", 1)
        redis.get("_healthcheck")
