import pytest

from vendor.julia import shortcuts, node


@pytest.mark.parametrize('qs, expected', [
    (
        '0[0][0][0]=1',
        {'0': {'0': {'0': {'0': '1'}}}}
    ),
    (
        '0=1&1[0][0]=foo&1[0][1]=bar&1[0][2][0]=ham&1[0][2][1]=baz',
        {'0': '1', '1': {'0': {'0': 'foo', '1': 'bar', '2': {'0': 'ham', '1': 'baz'}}}}
    ),
    # percent encoded
    (
        '0=1&1%5B0%5D%5B0%5D=foo&1%5B0%5D%5B1%5D=bar&1%5B0%5D%5B2%5D%5B0%5D=ham&1%5B0%5D%5B2%5D%5B1%5D=baz',
        {'0': '1', '1': {'0': {'0': 'foo', '1': 'bar', '2': {'0': 'ham', '1': 'baz'}}}}
    ),
    (
        'foo[bar]=ham&foo[bar]=baz&foo[spam]=eggs',
        {'foo': {'bar': ['ham', 'baz'], 'spam': 'eggs'}}
    ),
    (
        'foo=ham&foo=baz&foo=eggs',
        {'foo': ['ham', 'baz', 'eggs']}
    ),
    # shadowing
    (
        'foo[foo]=ham&foo[foo]=baz&foo=eggs',
        {'foo': {'foo': ['ham', 'baz']}}
    ),
])
def test_julia_v1_query_string_parser_ok_values(qs, expected):
    assert shortcuts.julia_v1(qs) == expected


@pytest.mark.parametrize('qs, expected', [
    (
        '0.0.0.0=1',
        {'0': {'0': {'0': {'0': '1'}}}}
    ),
    (
        '0=1&1.0.0=foo&1.0.1=bar&1.0.2.0=ham&1.0.2.1=baz',
        {'0': '1', '1': {'0': {'0': 'foo', '1': 'bar', '2': {'0': 'ham', '1': 'baz'}}}}
    ),
    (
        'foo.bar=ham&foo.bar=baz&foo.spam=eggs',
        {'foo': {'bar': ['ham', 'baz'], 'spam': 'eggs'}}
    ),
    (
        'foo=ham&foo=baz&foo=eggs',
        {'foo': ['ham', 'baz', 'eggs']}
    ),
    # shadowing
    (
        'foo.foo=ham&foo.foo=baz&foo=eggs',
        {'foo': {'foo': ['ham', 'baz']}}
    ),
    # ignoring empty components
    (
        'foo=ham&foo=baz&foo..=eggs',
        {'foo': ['ham', 'baz', 'eggs']}
    ),
])
def test_julia_v2_query_string_parser_ok_values(qs, expected):
    assert shortcuts.julia_v2(qs) == expected


class TestRootPatternNodeParser:
    test_pattern = {
        '0': {
            'type': node.StringPatternNode,
            'name': 'foo',
            'required': True,
        },
        '1': {
            'type': node.BooleanPatternNode,
            'name': 'bar',
        },
        '3': {
            'type': node.NumericPatternNode,
            'name': 'baz',
        },
        '4': {
            'type': node.DictPatternNode,
            'name': 'spam',
            'items': {
                '0': {
                    'type': node.StringPatternNode,
                    'name': 'eggs',
                },
                '1': {
                    'type': node.NumericPatternNode,
                    'name': '42',
                    'required': True,
                },
            },
        },
    }

    def test_root_pattern_node_instance(self):
        test_pattern_node = shortcuts.parse_pattern(self.test_pattern)
        assert isinstance(test_pattern_node, node.RootPatternNode)

    @pytest.mark.parametrize('ok_value', [
        '0=bar',
        '0=bar&1=1',
        '0=bar&1=1&4.0=foo&4.1=1',
    ])
    def test_root_pattern_node_parse_valid_values(self, ok_value):
        test_pattern_node = shortcuts.parse_pattern(self.test_pattern)
        assert isinstance(test_pattern_node.parse(shortcuts.julia_v2(ok_value)), node.BaseValueNode)

    @pytest.mark.parametrize('bad_value', [
        '0=bar&10=extra',  # unexpected item
        '0=bar&1=foo',  # invalid boolean value
        '0=bar&1=1&4.0=foo',  # required item missing
    ])
    def test_root_pattern_node_parse_invalid_values(self, bad_value):
        test_pattern_node = shortcuts.parse_pattern(self.test_pattern)
        with pytest.raises(node.ValueNodeError):
            test_pattern_node.parse(shortcuts.julia_v2(bad_value))


class TestMapValue:
    test_pattern = {
        '0': {
            'type': node.StringPatternNode,
            'name': 'foo',
        },
        '1': {
            'type': node.DictPatternNode,
            'name': 'spam',
            'items': {
                '0': {
                    'type': node.MappingPatternNode,
                    'name': 'eggs',
                    'table': {
                        '0': 'foo',
                        '1': 'bar',
                        '2': 'ham',
                    }
                },
                '1': {
                    'type': node.NumericPatternNode,
                    'name': '42',
                    'required': True,
                },
                '2': {
                    'type': node.DictPatternNode,
                    'name': 'foo',
                    'items': {
                        '0': {
                            'type': node.MappingPatternNode,
                            'name': '42',
                            'table': {
                                '0': '42',
                            }
                        },
                        '1': {
                            'type': node.DictPatternNode,
                            'name': 'bar',
                            'items': {
                                '0': {
                                    'type': node.MappingPatternNode,
                                    'name': 'spam',
                                    'table': {
                                        '0': 'foo',
                                        '1': 'bar',
                                        '2': 'bar',
                                        '3': 'foo',
                                        '4': 'ham',
                                    }
                                },
                                '1': {
                                    'type': node.NumericPatternNode,
                                    'name': '42',
                                    'required': True,
                                },
                            },
                        },
                    },
                },
            },
        },
        '2': {
            'type': node.BooleanPatternNode,
            'name': 'bar',
        },
        '3': {
            'type': node.MappingPatternNode,
            'name': 'baz',
            'table': {
                '0': 'ham',
                '1': 'spam',
                '2': 'eggs',
            }
        },
    }

    ok_values = (
        ('spam__eggs', '0', 'foo'),
        ('spam__eggs', '1', 'bar'),
        ('spam__eggs', '2', 'ham'),
        ('spam__foo__42', '0', '42'),
        ('baz', '0', 'ham'),
        ('baz', '1', 'spam'),
        ('baz', '2', 'eggs'),
        ('spam__eggs', ['0', '1', '2'], ['foo', 'bar', 'ham']),
        ('spam__eggs', ('0', '1'), ('foo', 'bar')),
        ('baz', ['0', '1', '2'], ['ham', 'spam', 'eggs']),
        ('baz', ('0', '1', '2'), ('ham', 'spam', 'eggs')),
        ('baz', ('0',), ('ham',)),
    )

    reverse_ok_values = (
        ('spam__foo__bar__spam', ['foo', 'bar'], ['0', '1', '2', '3']),
        ('spam__foo__bar__spam', ['foo'], ['0', '3']),
        ('spam__foo__bar__spam', 'foo', ['0', '3']),
        ('spam__foo__bar__spam', ['bar'], ['1', '2']),
        ('spam__foo__bar__spam', 'bar', ['1', '2']),
        ('spam__foo__bar__spam', 'ham', '4'),
    )

    @pytest.fixture
    def pattern_node(self):
        return shortcuts.parse_pattern(self.test_pattern)

    @pytest.mark.parametrize('name, value, expected', ok_values)
    def test_ok_values(self, pattern_node, name, value, expected):
        assert shortcuts.map(pattern_node, name, value) == expected

    @pytest.mark.parametrize('name, invalid_value', [
        ('spam__eggs', '4'),  # table value out of range
        ('spam__eggs', None),  # invalid key
        ('spam__eggs', 1),  # same
        ('baz', '5'),  # out of range
        (None, '0'),  # invalid name
        ('bar', '5'),  # not a mapping type
        ('spam__foo__42', '5'),  # same
    ])
    def test_map_invalid_values_raise_base_node_error(self, pattern_node, name, invalid_value):
        with pytest.raises(node.BaseNodeError):
            shortcuts.map(pattern_node, name, invalid_value)

    @pytest.mark.parametrize('name, value, expected', ok_values)
    def test_map_accepts_unparsed_pattern(self, name, value, expected):
        assert shortcuts.map(self.test_pattern, name, value) == expected

    @pytest.mark.parametrize('name, expected, value', ok_values)
    def test_unmap_ok_values(self, pattern_node, name, expected, value):
        assert shortcuts.unmap(pattern_node, name, value) == expected

    @pytest.mark.parametrize('name, value, expected', reverse_ok_values)
    def test_unmap_ok_values_reverse(self, pattern_node, name, value, expected):
        assert set(shortcuts.unmap(pattern_node, name, value)) == set(expected)

    @pytest.mark.parametrize('name, expected, value', ok_values)
    def test_unmap_accepts_unparsed_pattern(self, name, expected, value):
        assert shortcuts.unmap(self.test_pattern, name, value) == expected

    @pytest.mark.parametrize('name, value, tp, expected', [
        ('spam__foo__42', '0', str, '42'),
        ('spam__foo__42', '0', int, 42),
        ('spam__eggs', '0', str, 'foo'),
        ('spam__eggs', '0', bool, True),
    ])
    def test_map_coercion(self, name, value, tp, expected):
        assert shortcuts.map(self.test_pattern, name, value, coerce=tp) == expected

    @pytest.mark.parametrize('name, value, tp, expected', [
        ('spam__foo__bar__spam', 'ham', str, '4'),
        ('spam__foo__bar__spam', 'ham', int, 4),
    ])
    def test_unmap_coercion(self, name, value, tp, expected):
        assert shortcuts.unmap(self.test_pattern, name, value, coerce=tp) == expected

    @pytest.mark.parametrize('name, value, tp, expected', [
        ('spam__foo__bar__spam', ['foo', 'bar'], int, [0, 1, 2, 3]),
        ('spam__foo__bar__spam', ['foo', 'bar'], bool, [True, True, True, True]),
    ])
    def test_unmap_coercion_list(self, name, value, tp, expected):
        result = shortcuts.unmap(self.test_pattern, name, value, coerce=tp)
        assert len(result) == len(expected)
        assert set(result) == set(expected)
