import pytest

from apps.tracker.utils.parser import JuliaQueryString


class TestJuliaQueryString:
    @pytest.fixture
    def parser(self) -> JuliaQueryString:
        return JuliaQueryString()

    @pytest.mark.parametrize(
        "original, expected",
        [
            ("field=foo", {"field": "foo"}),
            ("field=foo&field=", {"field": ["foo", ""]}),
            ("field=foo&field=bar", {"field": ["foo", "bar"]}),
            ("field=foo&field=bar&field=bar", {"field": ["foo", "bar", "bar"]}),
            ("field%5B%5D=foo&field%5B%5D=bar&field%5B%5D=42", {"field[]": ["foo", "bar", "42"]}),
            (
                "field%5B0%5D=foo&field%5B1%5D=bar&field%5B3%5D=42",
                {"field[0]": "foo", "field[1]": "bar", "field[3]": "42"},
            ),
            ("field[]=foo&field[]=bar&field[]=42", {"field[]": ["foo", "bar", "42"]}),
            (
                "0=1&1[0][0]=foo&1[0][1]=bar&1[0][2][0]=ham&1[0][2][1]=baz",
                {
                    "0": "1",
                    "1[0][0]": "foo",
                    "1[0][1]": "bar",
                    "1[0][2][0]": "ham",
                    "1[0][2][1]": "baz",
                },
            ),
            # percent encoding
            ("name=john&password=plain%20text", {"name": "john", "password": "plain text"}),
            # encoding space with a plus sign
            (
                "first=this+is+a+field&second=was+it+clear+%28already%29%3F",
                {"first": "this is a field", "second": "was it clear (already)?"},
            ),
            # utf-8 percent encoded bytes
            (
                "message=%D0%97%D0%B4%D1%80%D0%B0%D0%B2%D1%81%D1%82%D0%B2%D1%83%D0%B9&message=%D0%9C%D0%B8%D1%80",
                {"message": ["Здравствуй", "Мир"]},
            ),
            (
                "42[0][0]=0&42[0][1]=foo&42[0][2]=bar&40[0][5]=42&42[0][50][]=foo",
                {
                    "42[0][0]": "0",
                    "42[0][1]": "foo",
                    "42[0][2]": "bar",
                    "40[0][5]": "42",
                    "42[0][50][]": "foo",
                },
            ),
            # improperly formed query strings get parsed, too
            ("foo", {"foo": ""}),
            ("foo&bar", {"foo": "", "bar": ""}),
            ("field=foo&", {"field": "foo"}),
            ("field=foo=bar=42&", {"field": "foo=bar=42"}),
            ("field&=foo=bar", {"field": "", "foo": "bar"}),
            ("foo[]", {"foo[]": ""}),
            ("foo[bar]", {"foo[bar]": ""}),
            ("", {}),
            ("[]", {"[]": ""}),
            ("&&", {}),
            ("[[][]]", {"[[][]]": ""}),
            ("foo[][]", {"foo[][]": ""}),
        ],
    )
    def test_parse_ok(self, parser: JuliaQueryString, original: str, expected: dict):
        parser.parse(original)
        assert parser == expected

    def test_parser_behaves_like_dict(self, parser: JuliaQueryString):
        assert isinstance(parser, dict)
        parser["foo"] = "bar"
        assert parser["foo"] == "bar"

    def test_parse_raw_querystring(self, parser: JuliaQueryString):
        parser.parse("field1=foo&field2=bar&field3=baz")
        assert parser["field1"] == "foo"
        assert parser["field2"] == "bar"
        assert parser["field3"] == "baz"

    def test_parse_params_with_duplicate_keys(self, parser: JuliaQueryString):
        parser.parse("foo=bar&foo=ham&foo=baz")
        assert parser["foo"] == ["bar", "ham", "baz"]

    def test_the_parser_instance_is_returned(self, parser: JuliaQueryString):
        parsed = parser.parse("foo=bar&foo=ham&foo=baz")
        assert parser is parsed
        assert parsed == {"foo": ["bar", "ham", "baz"]}


class TestQueryStringArrayExpansion:
    @pytest.fixture
    def parser(self) -> JuliaQueryString:
        return JuliaQueryString()

    @pytest.mark.parametrize(
        "original, expected",
        [
            # overlapped parameter keys get shadowed
            (
                {
                    "field[foo][0]": "bar",
                    "field[foo][1]": "ham",
                    "field[foo][42]": "baz",
                    "field[foo]": "spam",
                },
                {"field": {"foo": {"0": "bar", "1": "ham", "42": "baz"}}},
            ),
            (
                {"field[foo][0]": "bar", "field[foo][1]": "ham", "field[foo]": "spam"},
                {"field": {"foo": {"0": "bar", "1": "ham"}}},
            ),
            (
                {
                    "0": "1",
                    "1[0][0]": "foo",
                    "1[0][1]": "bar",
                    "1[0][2][0]": "ham",
                    "1[0][2][1]": "baz",
                },
                {"0": "1", "1": {"0": {"0": "foo", "1": "bar", "2": {"0": "ham", "1": "baz"}}}},
            ),
            # remove brackets
            ({"field[]": ["foo", "bar", "42"]}, {"field": ["foo", "bar", "42"]}),
            (
                {"field[0]": "foo", "field[1]": "bar", "field[3]": "42"},
                {"field": {"0": "foo", "1": "bar", "3": "42"}},
            ),
            (
                {
                    "42[0][0]": "0",
                    "42[0][1]": "foo",
                    "42[0][2]": "bar",
                    "40[0][5]": "42",
                    "42[0][50][]": "foo",
                },
                {
                    "40": {"0": {"5": "42"}},
                    "42": {"0": {"0": "0", "1": "foo", "2": "bar", "50": ["foo"]}},
                },
            ),
            ({"foo[]": ""}, {"foo": [""]}),
            ({"foo[bar]": ""}, {"foo": {"bar": ""}}),
            # invalid tokens dont get parsed
            ({"[]": ""}, {}),
            ({"[[][]]": ""}, {}),
            ({"foo[][]": ""}, {}),
            # no changes to the original dicts
            ({}, {}),
            ({"field": "foo"}, {"field": "foo"}),
            ({"field": ["foo", ""]}, {"field": ["foo", ""]}),
            ({"field": ["foo", "bar"]}, {"field": ["foo", "bar"]}),
            ({"field": ["foo", "bar", "bar"]}, {"field": ["foo", "bar", "bar"]}),
            (
                {"name": "john", "password": "plain text"},
                {"name": "john", "password": "plain text"},
            ),
            (
                {"first": "this is a field", "second": "was it clear (already)?"},
                {"first": "this is a field", "second": "was it clear (already)?"},
            ),
            ({"message": ["Здравствуй", "Мир"]}, {"message": ["Здравствуй", "Мир"]}),
            ({"foo": ""}, {"foo": ""}),
            ({"foo": "", "bar": ""}, {"foo": "", "bar": ""}),
            ({"field": "foo=bar=42"}, {"field": "foo=bar=42"}),
            ({"field": "", "foo": "bar"}, {"field": "", "foo": "bar"}),
        ],
    )
    def test_array_expansion(self, original: dict, expected: dict):
        parser = JuliaQueryString(original)
        parser.expand_array()
        assert parser == expected

    def test_uri_array_expansion_on_demand(self, parser: JuliaQueryString):
        parser.parse("field[spam]=foo&field[eggs][42]=bar&field[ham][spam][eggs]=baz")
        assert parser == {
            "field[spam]": "foo",
            "field[eggs][42]": "bar",
            "field[ham][spam][eggs]": "baz",
        }

        parser.expand_array()
        assert parser == {
            "field": {"spam": "foo", "eggs": {"42": "bar"}, "ham": {"spam": {"eggs": "baz"}}}
        }

    def test_the_parser_instance_is_returned(self, parser: JuliaQueryString):
        parser.parse("field[spam]=foo&field[eggs][42]=bar&field[ham][spam][eggs]=baz")
        parsed = parser.expand_array()
        assert parser is parsed
        assert parsed == {
            "field": {"spam": "foo", "eggs": {"42": "bar"}, "ham": {"spam": {"eggs": "baz"}}}
        }


class TestQueryStringDotExpansion:
    @pytest.fixture
    def parser(self) -> JuliaQueryString:
        return JuliaQueryString()

    @pytest.mark.parametrize(
        "original, expected",
        [
            ({"foo.bar": ""}, {"foo": {"bar": ""}}),
            (
                {"field.foo.0": "bar", "field.foo.1": "ham", "field.foo": "spam"},
                {"field": {"foo": {"0": "bar", "1": "ham"}}},
            ),
            (
                {"field.0": "foo", "field.1": "bar", "field.3": "42"},
                {"field": {"0": "foo", "1": "bar", "3": "42"}},
            ),
            (
                {"42.0.0": "0", "42.0.1": "foo", "42.0.2": "bar", "40.0.5": "42", "42.0.50": "foo"},
                {
                    "40": {"0": {"5": "42"}},
                    "42": {"0": {"0": "0", "1": "foo", "2": "bar", "50": "foo"}},
                },
            ),
            # overlapping keys get shadowed
            ({"foo.bar": "baz", "foo": "ham"}, {"foo": {"bar": "baz"}}),
            (
                {
                    "field.foo.0.": "bar",
                    "field.foo.1": "ham",
                    "field.foo.42": "baz",
                    "field.foo.": "spam",
                },
                {"field": {"foo": {"0": "bar", "1": "ham", "42": "baz"}}},
            ),
            # square brackets are untouched
            ({"field[]": ["foo", "bar", "42"]}, {"field[]": ["foo", "bar", "42"]}),
            ({"foo[]": ""}, {"foo[]": ""}),
            ({"[]": ""}, {"[]": ""}),
            ({"[[][]]": ""}, {"[[][]]": ""}),
            ({"foo[][]": ""}, {"foo[][]": ""}),
            # invalid tokens are not parsed
            ({".": ""}, {}),
            ({"...": ""}, {}),
            ({".foo": ""}, {"foo": ""}),
            ({".foo...": ""}, {"foo": ""}),
            # no changes to the original dicts
            ({}, {}),
            ({"field": "foo"}, {"field": "foo"}),
            ({"field": ["foo", ""]}, {"field": ["foo", ""]}),
            ({"field": ["foo", "bar"]}, {"field": ["foo", "bar"]}),
            ({"field": ["foo", "bar", "bar"]}, {"field": ["foo", "bar", "bar"]}),
            (
                {"name": "john", "password": "plain text"},
                {"name": "john", "password": "plain text"},
            ),
            (
                {"first": "this is a field", "second": "was it clear (already)?"},
                {"first": "this is a field", "second": "was it clear (already)?"},
            ),
            ({"message": ["Здравствуй", "Мир"]}, {"message": ["Здравствуй", "Мир"]}),
            ({"foo": ""}, {"foo": ""}),
            ({"foo": "", "bar": ""}, {"foo": "", "bar": ""}),
            ({"field": "foo=bar=42"}, {"field": "foo=bar=42"}),
            ({"field": "", "foo": "bar"}, {"field": "", "foo": "bar"}),
        ],
    )
    def test_parse_ok(self, original, expected):
        parser = JuliaQueryString(original)
        parser.expand_dots()
        assert parser == expected

    def test_expand_dots_on_demand(self, parser: JuliaQueryString):
        parser.parse("field.spam=foo&field.eggs.42=bar&field.ham.spam.eggs=baz")
        assert parser == {"field.spam": "foo", "field.eggs.42": "bar", "field.ham.spam.eggs": "baz"}

        parser.expand_dots()
        assert parser == {
            "field": {"spam": "foo", "eggs": {"42": "bar"}, "ham": {"spam": {"eggs": "baz"}}}
        }

    def test_the_parser_instance_is_returned(self, parser: JuliaQueryString):
        parser.parse("field.spam=foo&field.eggs.42=bar&field.ham.spam.eggs=baz")
        parsed = parser.expand_dots()
        assert parser is parsed
        assert parsed == {
            "field": {"spam": "foo", "eggs": {"42": "bar"}, "ham": {"spam": {"eggs": "baz"}}}
        }
