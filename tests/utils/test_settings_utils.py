import logging
import os
from unittest import mock

import pytest

from apps.utils.settings import env, env_bool, env_list, env_log_level


@pytest.mark.parametrize(
    "name, default, expected",
    [
        ("SETTINGS_REDIS_HOST", "0.0.0.0", "127.0.0.1"),
        ("SETTINGS_REDIS_PORT", 6379, 6379),
    ],
)
@mock.patch.dict(os.environ, {"SETTINGS_REDIS_HOST": "127.0.0.1"})
def test_env(name, default, expected):
    assert env(name, default) == expected


@pytest.mark.parametrize(
    "value, default, expected",
    [
        # true-values
        ("True", False, True),
        ("TRUE", False, True),
        ("true", False, True),
        ("t", False, True),
        ("Yes", False, True),
        ("yes", False, True),
        ("yeS", False, True),
        ("y", False, True),
        ("1", False, True),
        # false values
        ("False", True, False),
        ("FALSE", True, False),
        ("false", True, False),
        ("f", True, False),
        ("No", True, False),
        ("NO", True, False),
        ("n", True, False),
        ("0", True, False),
        # default values
        ("", True, True),
        ("", False, False),
    ],
)
def test_env_bool(value, default, expected):
    with mock.patch.dict(os.environ, {"SETTINGS_ENABLE_DEBUG": value}):
        assert env_bool("SETTINGS_ENABLE_DEBUG", default=default) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("", []),
        (",", []),
        (",,,,", []),
        (", ,", []),
        ("swat4stats.com", ["swat4stats.com"]),
        ("swat4stats.com ", ["swat4stats.com"]),
        ("swat4stats.com ,", ["swat4stats.com"]),
        ("swat4stats.com,", ["swat4stats.com"]),
        (",swat4stats.com,", ["swat4stats.com"]),
        ("swat4stats.com,swat4stats.test", ["swat4stats.com", "swat4stats.test"]),
        ("swat4stats.com,,swat4stats.test", ["swat4stats.com", "swat4stats.test"]),
        ("swat4stats.com, ,swat4stats.test", ["swat4stats.com", "swat4stats.test"]),
    ],
)
def test_env_list(value, expected):
    with mock.patch.dict(os.environ, {"SETTINGS_ALLOWED_HOSTS": value}):
        assert env_list("SETTINGS_ALLOWED_HOSTS") == expected


@pytest.mark.parametrize(
    "value, default, expected",
    [
        ("", "INFO", "INFO"),
        ("ERROR", "INFO", "ERROR"),
    ],
)
def test_env_log_level(value, default, expected):
    with mock.patch.dict(os.environ, {"SETTINGS_LOG_LEVEL": value}):
        assert env_log_level("SETTINGS_LOG_LEVEL", default) == expected


def test_env_log_level_validate():
    with mock.patch.dict(os.environ, {"SETTINGS_LOG_LEVEL": "info"}), pytest.raises(
        ValueError, match='"info" is not a valid logging level'
    ):
        env_log_level("SETTINGS_LOG_LEVEL", "ERROR")


@pytest.mark.parametrize(
    "value, default, not_lower, expected",
    [
        ("", "INFO", logging.INFO, "INFO"),
        ("", "INFO", logging.WARNING, "WARNING"),
        ("INFO", "INFO", logging.WARNING, "WARNING"),
        ("INFO", "ERROR", logging.WARNING, "WARNING"),
        ("WARNING", "INFO", logging.WARNING, "WARNING"),
        ("WARNING", "ERROR", logging.WARNING, "WARNING"),
        ("ERROR", "INFO", logging.WARNING, "ERROR"),
        ("ERROR", "CRITICAL", logging.WARNING, "ERROR"),
    ],
)
def test_env_log_level_not_lower(value, default, not_lower, expected):
    with mock.patch.dict(os.environ, {"SETTINGS_LOG_LEVEL": value}):
        assert env_log_level("SETTINGS_LOG_LEVEL", default, not_lower) == expected
