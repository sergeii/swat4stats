import pytest
from voluptuous import Invalid, Optional, Schema

from apps.utils.schema import FallbackMapping, Mapping, OptionalMapping


class TestMapping:
    def test_key_mapping(self):
        schema = Schema(
            {
                Mapping({"foo": "bar"}): int,
                Mapping({"ham": 1}): str,
                Mapping({"spam": None}): int,
            },
            required=True,
        )
        data = {
            "foo": 123,
            "ham": "test",
            "spam": 789,
        }
        assert schema(data) == {
            "bar": 123,
            1: "test",
            None: 789,
        }

    def test_error_if_keys_are_missing(self):
        schema = Schema(
            {
                Mapping({"foo": "bar"}): int,
                Mapping({"spam": "eggs"}): str,
            },
            required=True,
        )
        data = {
            "foo": 123,
        }
        with pytest.raises(Invalid):
            schema(data)

    def test_missing_keys_is_accepted(self):
        schema = Schema(
            {
                Mapping({"foo": "bar"}): int,
                Mapping({"spam": "eggs"}): str,
            }
        )
        data = {
            "foo": 123,
        }
        assert schema(data) == {"bar": 123}

    def test_exception_is_raised_if_extra_keys(self):
        schema = Schema(
            {
                Mapping({"foo": "bar"}): int,
                Mapping({"spam": "eggs"}): str,
            }
        )
        data = {
            "foo": 123,
            "ham": 42,
            "spam": None,
        }
        with pytest.raises(Invalid):
            schema(data)

    def test_key_mapping_is_optional(self):
        schema = Schema(
            {
                Mapping({"foo": "bar"}): int,
                Optional(Mapping({"spam": "eggs"})): int,
            },
            required=True,
        )
        assert schema({"foo": 123, "spam": 456}) == {"bar": 123, "eggs": 456}
        assert schema({"foo": 123}) == {"bar": 123}

    def test_value_mapping(self):
        schema = Schema(
            {
                "spam": Mapping({"eggs": "eggs!"}),
                "ham": Mapping({"baz": "baz!"}),
            }
        )
        data = {
            "spam": "eggs",
            "ham": "baz",
        }
        assert schema(data) == {"spam": "eggs!", "ham": "baz!"}

    def test_multivalue_mapping(self):
        schema = Schema(
            {
                "item": Mapping({"foo": "bar", "spam": "eggs"}),
            }
        )
        assert schema({"item": "foo"}) == {"item": "bar"}
        assert schema({"item": "spam"}) == {"item": "eggs"}
        with pytest.raises(Invalid):
            schema({"item": "unknown"})


class TestOptionalMapping:
    def test_optional_key_mapping_defaults_to_value(self):
        schema = Schema(
            {
                Mapping({"foo": "bar"}): int,
                OptionalMapping({"spam": "eggs"}, default=42): int,
            },
            required=True,
        )
        assert schema({"foo": 123, "spam": 456}) == {"bar": 123, "eggs": 456}
        assert schema({"foo": 123}) == {"bar": 123, "eggs": 42}


class TestFallbackMapping:
    def test_value_stays_same_if_not_mapped(self):
        schema = Schema(
            {
                "key1": FallbackMapping({"foo": "bar"}),
                "key2": FallbackMapping({"spam": "eggs", "answer": 42}),
            },
            required=True,
        )
        assert schema({"key1": "foo", "key2": "baz"}) == {"key1": "bar", "key2": "baz"}
        assert schema({"key1": "foo", "key2": "answer"}) == {"key1": "bar", "key2": 42}
