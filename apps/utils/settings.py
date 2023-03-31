import logging
import os
from typing import Any


def env(name: str, default: Any) -> Any:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool) -> bool:
    if value := os.environ.get(name):
        if value[0].lower() in ('y', 't', '1'):
            return True
    return default


def env_list(name: str) -> list[str]:
    values = []
    if values_str := os.environ.get(name):
        for value in values_str.split(','):
            if value_clean := value.strip():
                values.append(value_clean)
    return values


def env_log_level(name: str, default: str, not_lower: int | None = None) -> str:
    if value := os.environ.get(name):
        level_int = logging.getLevelName(value)
        if not isinstance(level_int, int):
            raise ValueError(f'"{value}" is not a valid logging level')
        if not_lower is not None and level_int < not_lower:
            return logging.getLevelName(not_lower)
        return logging.getLevelName(level_int)
    return default
