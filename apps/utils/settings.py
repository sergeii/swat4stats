import logging
import os
from typing import Any


def env(name: str, default: Any) -> Any:
    return os.environ.get(name, default)


def env_bool(name: str, *, default: bool) -> bool:
    if value := os.environ.get(name):
        return value[0].lower() in ("y", "t", "1")
    return default


def env_list(name: str) -> list[str]:
    values = []
    if values_str := os.environ.get(name):
        for value in values_str.split(","):
            if value_clean := value.strip():
                values.append(value_clean)  # noqa: PERF401
    return values


def env_log_level(name: str, default: str, not_lower: int | None = None) -> str:
    value = os.environ.get(name) or default
    level_int = logging.getLevelName(value)

    if not isinstance(level_int, int):
        err_msg = f'"{value}" is not a valid logging level'
        raise ValueError(err_msg)

    if not_lower is not None and level_int < not_lower:
        return logging.getLevelName(not_lower)

    return logging.getLevelName(level_int)
