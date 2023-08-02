import logging
from typing import Any

from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    # Ensure detail of a ValidationError instance is a dict
    if isinstance(exc, ValidationError) and isinstance(exc.detail, list):
        exc = ValidationError(detail=as_serializer_error(exc))
    return drf_exception_handler(exc, context)
