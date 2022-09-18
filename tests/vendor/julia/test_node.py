from copy import deepcopy

import pytest

from vendor.julia import node


class TestBaseValueNode:

    class NodeWithBaseValue(node.BasePatternNode):
        value_class = node.BaseValueNode

        def clean(self, value):
            return value

    def test_value_node_keeps_reference_to_pattern_node(self):
        pattern_node = self.NodeWithBaseValue()
        value_node = pattern_node.parse('foo')
        assert value_node.pattern is pattern_node

    def test_value_node_keeps_track_of_raw_value(self):
        pattern_node = self.NodeWithBaseValue()
        value_node = pattern_node.parse('foo')
        assert value_node.raw == 'foo'

    def test_value_node_has_empty_parsed_value(self):
        value_node = node.BaseValueNode('foo', None)
        assert value_node.value is None


class TestDictValueNode:

    class NodeWithDictValue(node.BasePatternNode):

        value_class = node.DictValueNode

        def clean(self, value):
            return value

    def test_dict_value_node_is_a_dict_instance(self):
        value_node = node.DictValueNode(None, None)
        assert isinstance(value_node, dict)

    def test_dict_value_node_behaves_like_dict(self):
        value_node = node.DictValueNode(None, None)

        value_node['foo'] = 'bar'
        assert value_node['foo'] == 'bar'

        del value_node['foo']
        with pytest.raises(KeyError):
            value_node['foo']

    def test_dict_value_node_behaves_like_value_node(self):
        pattern_node = self.NodeWithDictValue()
        value_node = pattern_node.parse({'foo': 'bar', 'ham': 'baz'})
        assert value_node.pattern is pattern_node
        assert value_node.raw == {'foo': 'bar', 'ham': 'baz'}


class TestListValueNode:

    class NodeWithListValue(node.BasePatternNode):
        value_class = node.ListValueNode

        def clean(self, value):
            return value

    def test_list_value_node_is_a_list_instance(self):
        value_node = node.ListValueNode(None, None)
        assert isinstance(value_node, list)

    def test_list_value_node_behaves_like_a_list(self):
        value_node = node.ListValueNode(None, None)

        value_node.append('foo')
        value_node.append('bar')

        assert value_node[0] == 'foo'
        assert value_node[1] == 'bar'

        del value_node[0]
        assert value_node[0] == 'bar'

        with pytest.raises(IndexError):
            value_node[1]

    def test_list_value_node_behaves_like_a_value_node(self):
        pattern_node = self.NodeWithListValue()
        value_node = pattern_node.parse(['foo', 'bar', 'ham'])
        assert value_node.pattern is pattern_node
        assert value_node.raw == ['foo', 'bar', 'ham']


class TestBasePatternNode:

    def test_base_pattern_node_doesnt_accept_args(self):
        with pytest.raises(TypeError):
            node.BasePatternNode('foo', 'bar')

    def test_base_pattern_node_doesnt_accept_more_kwargs(self):
        with pytest.raises(node.PatternNodeError):
            node.BasePatternNode(foo='foo', bar='bar')

    def test_clean_raises_non_implemented_error(self):
        pattern_node = node.BasePatternNode()
        with pytest.raises(NotImplementedError):
            pattern_node.parse('bar')


class TestRequiredValueMixin:

    class ClassWithRequiredValue(node.RequiredValueMixin, node.BasePatternNode):

        def clean(self, value):
            return value

    def test_node_with_no_value(self):
        pattern_node = self.ClassWithRequiredValue()
        value_node = pattern_node.parse(None)
        assert value_node is None

    def test_unrequired_node_with_no_value(self):
        pattern_node = self.ClassWithRequiredValue(required=False)
        value_node = pattern_node.parse(None)
        assert value_node is None

    def test_required_node_with_no_value(self):
        pattern_node = self.ClassWithRequiredValue(required=True)
        with pytest.raises(node.ValueNodeError):
            pattern_node.parse(None)

    def test_required_node_with_value(self):
        pattern_node = self.ClassWithRequiredValue(required=True)
        value_node = pattern_node.parse('foo')
        assert value_node.raw == 'foo'

    @pytest.mark.parametrize('truthy_value', [True, 1, '1', '0'])
    def test_node_accepts_truthy_values_only(self, truthy_value):
        pattern_node = self.ClassWithRequiredValue(required=truthy_value)
        with pytest.raises(node.ValueNodeError):
            pattern_node.parse(None)

    @pytest.mark.parametrize('falsy_value', [False, 0, None, ''])
    def test_node_accepts_falsy_values(self, falsy_value):
        pattern_node = self.ClassWithRequiredValue(required=falsy_value)
        value_node = pattern_node.parse(None)
        assert value_node is None


class TestDefaultValueMixin:

    class ClassWithDefaultValue(node.DefaultValueMixin, node.BasePatternNode):

        def clean(self, value):
            return value

    def test_default_node_with_no_value(self):
        pattern_node = self.ClassWithDefaultValue(default='foo')
        value_node = pattern_node.parse(None)
        assert value_node.raw == 'foo'

    def test_default_node_with_value(self):
        pattern_node = self.ClassWithDefaultValue(default='foo')
        value_node = pattern_node.parse('bar')
        assert value_node.raw == 'bar'

    def test_non_default_node_with_value(self):
        pattern_node = self.ClassWithDefaultValue(default=None)
        value_node = pattern_node.parse('bar')
        assert value_node.raw == 'bar'


class TestRequiredDefaultMixin:

    class ClassWithRequiredDefaultValue(node.RequiredValueMixin, node.DefaultValueMixin, node.BasePatternNode):

        def clean(self, value):
            return value

    def test_required_default_node_with_no_value_fails(self):
        pattern_node = self.ClassWithRequiredDefaultValue(required=True, default='foo')
        with pytest.raises(node.ValueNodeError):
            pattern_node.parse(None)

    def test_unrequired_default_node_with_no_value_returns_default(self):
        pattern_node = self.ClassWithRequiredDefaultValue(required=False, default='foo')
        value_node = pattern_node.parse(None)
        assert value_node.raw == 'foo'

    def test_unrequired_default_node_with_value_returns_value(self):
        pattern_node = self.ClassWithRequiredDefaultValue(required=False, default='foo')
        value_node = pattern_node.parse('bar')
        assert value_node.raw == 'bar'

    def test_required_default_node_with_value_returns_value(self):
        pattern_node = self.ClassWithRequiredDefaultValue(required=True, default='foo')
        value_node = pattern_node.parse('bar')
        assert value_node.raw == 'bar'


class TestStringNode:

    @pytest.mark.parametrize('raw, expected', [
        ('0', '0'),
        ('foo', 'foo'),
        (b'bar', 'bar'),
        (0, '0'),
        (110, '110'),
        (True, 'True'),
        ('', ''),
        (b'', ''),
        ('42', '42'),
        (b'42', '42'),
        (42, '42'),
        ([42], '[42]'),
    ])
    def test_string_node_parsed_value_is_a_unicode_string(self, raw, expected):
        string_pattern_node = node.StringPatternNode()
        string_value_node = string_pattern_node.parse(raw)
        assert string_value_node.value == expected

    def test_string_node_parse_none_returns_none(self):
        string_pattern_node = node.StringPatternNode()
        assert string_pattern_node.parse(None) is None

    def test_string_node_parse_none_returns_none_unless_required(self):
        string_pattern_node = node.StringPatternNode(required=True)
        with pytest.raises(node.ValueNodeError):
            string_pattern_node.parse(None)

    def test_string_node_parse_none_returns_none_unless_default(self):
        string_pattern_node = node.StringPatternNode(default='foo')
        assert string_pattern_node.parse(None).value == 'foo'


class TestNumericNode:

    @pytest.mark.parametrize('raw, expected', [
        ('-100', -100),
        ('10.12', 10.12),
        ('-1.12', -1.12),
        ('0', 0),
        ('1', 1),
        (b'0', 0),
        ('0', 0),
        (b'1', 1),
        (0, 0),
        (1, 1),
        ('-42', -42),
        (True, 1),
        (False, 0),
    ])
    def test_numeric_node_parsed_value_is_a_number(self, raw, expected):
        numeric_pattern_node = node.NumericPatternNode()
        numeric_value_node = numeric_pattern_node.parse(raw)
        assert numeric_value_node.value == expected

    @pytest.mark.parametrize('invalid_value', [
        'foo',
        b'bar',
        [],
        {},
        '',
        lambda x: x,
    ])
    def test_numeric_node_parse_fails_on_invalid_input(self, invalid_value):
        numeric_pattern_node = node.NumericPatternNode()
        with pytest.raises(node.ValueNodeError):
            numeric_pattern_node.parse(invalid_value)

    def test_numeric_node_parse_none_returns_none(self):
        numeric_pattern_node = node.NumericPatternNode()
        assert numeric_pattern_node.parse(None) is None

    def test_numeric_node_parse_none_returns_none_unless_required(self):
        numeric_pattern_node = node.NumericPatternNode(required=True)
        with pytest.raises(node.ValueNodeError):
            numeric_pattern_node.parse(None)

    def test_numeric_node_parse_none_returns_none_unless_default(self):
        numeric_pattern_node = node.NumericPatternNode(default='10')
        assert numeric_pattern_node.parse(None).value == 10


class TestMappingPatternNode:

    @pytest.fixture
    def test_table(self):
        return {'foo': 'bar', 'spam': 'eggs', 'baz': 'ham', 'question': 42, 'truth': True}

    @pytest.mark.parametrize('valid', [
        {'foo': 'bar', 'spam': 'eggs', 'baz': 'ham', 'question': 42, 'truth': True},
        (('foo', 'bar'), ('spam', 'eggs')),
        [],  # empty mapping
        (),  # same
    ])
    def test_mapping_node_accepts_table_as_keyword_argument(self, valid):
        node.MappingPatternNode(table=valid)
        node.MappingPatternNode(valid)

    @pytest.mark.parametrize('invalid', [
        'foo',
        42,
        ('foo', 'bar'),
    ])
    def test_mapping_node_fails_on_invalid_mapping_table(self, invalid):
        with pytest.raises(node.PatternNodeError):
            node.MappingPatternNode(table=invalid)

        with pytest.raises(node.PatternNodeError):
            node.MappingPatternNode(invalid)

    def test_mapping_node_maps_key_to_value_on_valid_key(self, test_table):
        for test_key, test_value in test_table.items():
            mapping_pattern_node = node.MappingPatternNode(table=test_table)
            assert mapping_pattern_node.parse(test_key).value == test_value

    def test_mapping_node_maps_fails_to_map_nonexistent_key(self, test_table):
        mapping_pattern_node = node.MappingPatternNode(table=test_table)
        with pytest.raises(node.ValueNodeError):
            mapping_pattern_node.parse('nonexistent')

    def test_mapping_node_default_key_value(self, test_table):
        for test_key, test_value in test_table.items():
            mapping_pattern_node = node.MappingPatternNode(table=test_table, default=test_key)
            assert mapping_pattern_node.parse(None).value == test_value

    def test_mapping_node_required_passes_non_empty_value(self, test_table):
        mapping_pattern_node = node.MappingPatternNode(table=test_table, required=True)
        for test_key, test_value in test_table.items():
            assert mapping_pattern_node.parse(test_key).value == test_value

    def test_mapping_node_parse_none_returns_none(self, test_table):
        mapping_pattern_node = node.MappingPatternNode(table=test_table)
        assert mapping_pattern_node.parse(None) is None

    def test_mapping_node_parse_none_returns_none_unless_required(self, test_table):
        mapping_pattern_node = node.MappingPatternNode(table=test_table, required=True)
        with pytest.raises(node.ValueNodeError):
            mapping_pattern_node.parse(None)

    def test_mapping_node_parse_none_returns_none_unless_default(self, test_table):
        mapping_pattern_node = node.MappingPatternNode(table=test_table, default='foo')
        assert mapping_pattern_node.parse(None).value == 'bar'

    def test_mapping_node_required_ignores_default_value_on_empty_input(self, test_table):
        mapping_pattern_node = node.MappingPatternNode(table=test_table, required=True, default='foo')
        with pytest.raises(node.ValueNodeError):
            mapping_pattern_node.parse(None)

    def test_mapping_reverse_values(self, test_table):
        for test_key, test_value in test_table.items():
            mapping_pattern_node = node.MappingPatternNode(table=test_table)
            assert mapping_pattern_node.reverse(test_value) == test_key

    def test_mapping_reverse_same_value_to_multiple_keys(self):
        table = {
            '0': 'foo',
            '1': 'foo',
            '2': 'bar',
            '3': 'ham',
            '42': 'bar',
            '44': 'bar',
            '45': 'spam',
        }
        test_node = node.MappingPatternNode(table=table)

        assert set(test_node.reverse('foo')) == {'0', '1'}
        assert set(test_node.reverse('bar')) == {'2', '42', '44'}
        assert test_node.reverse('ham') == '3'
        assert test_node.reverse('spam') == '45'


class TestBooleanPattenNode:

    @pytest.mark.parametrize('ok_value, expected', [
        ('1', True),
        ('10', True),
        (b'0', False),
        ('0', False),
        (b'1', True),
        (0, False),
        (1, True),
        (2, True),
        (3, True),
        (True, True),
        (False, False),
    ])
    def test_boolean_node_expected_value(self, ok_value, expected):
        boolean_pattern_node = node.BooleanPatternNode()
        assert boolean_pattern_node.parse(ok_value).value == expected

    @pytest.mark.parametrize('bad_value', ['foo', b'bar', [], {}, '', '-10.1'])
    def test_boolean_node_invalid_values(self, bad_value):
        boolean_pattern_node = node.BooleanPatternNode()
        with pytest.raises(node.ValueNodeError):
            boolean_pattern_node.parse(bad_value)

    def test_boolean_node_parse_none_returns_none(self):
        boolean_pattern_node = node.BooleanPatternNode()
        assert boolean_pattern_node.parse(None) is None

    @pytest.mark.parametrize('truthy_value', [True, 1, '1', b'1', '10', b'10'])
    def test_boolean_node_parse_none_returns_none_unless_truthy_default(self, truthy_value):
        boolean_pattern_node = node.BooleanPatternNode(default=truthy_value)
        assert boolean_pattern_node.parse(None).value is True

    @pytest.mark.parametrize('falsy_value', [False, 0, '0', b'0'])
    def test_boolean_node_parse_none_returns_none_unless_falsy_default(self, falsy_value):
        boolean_pattern_node = node.BooleanPatternNode(default=falsy_value)
        assert boolean_pattern_node.parse(None).value is False


class TestListPatternNode:

    @pytest.fixture
    def test_item(self):
        return {'type': node.StringPatternNode, 'default': 'lol'}

    def test_list_pattern_node_fails_without_item_kwarg(self):
        with pytest.raises(node.PatternNodeError):
            node.ListPatternNode()

    def test_list_pattern_node_is_allowed_to_pass_item_as_positional_argument(self, test_item):
        pattern_node = node.ListPatternNode(test_item)
        assert isinstance(pattern_node.item, node.StringPatternNode)

    @pytest.mark.parametrize('valid_item', [
        {'type': node.BooleanPatternNode, 'required': False},
        {'type': node.NumericPatternNode, 'required': True},
        {'type': node.BooleanPatternNode, 'required': False},
        {'type': node.ListPatternNode,
         'item': {'type': node.ListPatternNode,
                  'item': {'type': node.StringPatternNode}}},
    ])
    @pytest.mark.parametrize('node_factory', [
        lambda item: node.ListPatternNode(item=item),
        lambda item: node.ListPatternNode(item),
    ], ids=['kwarg', 'arg'])
    def test_list_pattern_node_passes_valid_item(self, node_factory, valid_item):
        item_type = valid_item['type']
        list_pattern_node = node_factory(deepcopy(valid_item))
        assert isinstance(list_pattern_node.item, item_type)

    @pytest.mark.parametrize('invalid_item', [
        None,
        {},  # no type #1
        {'default': 'bar'},  # no type #2
        {'type': str},  # invalid type #1
        {'type': int},  # invalid type #2
        {'type': None},  # invalid type #3
        {'something_different': 'bar'},
        {'type': node.BooleanPatternNode,
         'default': 'bar',
         'required': False,
         'irrelevant_arg': 'ham'},  # extra kwarg
    ])
    @pytest.mark.parametrize('node_factory', [
        lambda item: node.ListPatternNode(item=item),
        lambda item: node.ListPatternNode(item),
    ], ids=['kwarg', 'arg'])
    def test_list_pattern_node_fails_with_invalid_item_kwarg(self, node_factory, invalid_item):
        with pytest.raises(node.PatternNodeError):
            node_factory(invalid_item)

    def test_list_pattern_node_parse_returns_list(self, test_item):
        list_pattern_node = node.ListPatternNode(item=test_item)
        list_value_node = list_pattern_node.parse(['foo', 'bar', 'ham'])
        assert isinstance(list_value_node, list)
        assert isinstance(list_value_node, node.ListValueNode)

    def test_list_pattern_node_parse_list_returns_parsed_list_elements(self, test_item):
        list_pattern_node = node.ListPatternNode(item=test_item)
        list_value_node = list_pattern_node.parse(['foo', 'bar', 'ham'])
        assert len(list_value_node) == 3
        for parsed_item in list_value_node:
            assert isinstance(parsed_item.pattern, node.StringPatternNode)
            assert parsed_item.value in ('foo', 'bar', 'ham')

    def test_list_pattern_node_parse_dict_returns_parsed_dict_values(self, test_item):
        list_pattern_node = node.ListPatternNode(item=test_item)
        list_value_node = list_pattern_node.parse({'0': 'foo', '20': 'bar', 'spam': 'eggs'})
        assert len(list_value_node) == 3
        for parsed_item in list_value_node:
            assert isinstance(parsed_item.pattern, node.StringPatternNode)
            assert parsed_item.value in ('foo', 'bar', 'eggs')

    def test_list_value_node_parsed_attr_remains_none(self, test_item):
        list_pattern_node = node.ListPatternNode(item=test_item)
        list_value_node = list_pattern_node.parse(['foo', 'bar', 'ham'])
        assert list_value_node.value is None

    def test_list_pattern_node_parse_none_returns_none(self, test_item):
        list_pattern_node = node.ListPatternNode(item=test_item)
        assert list_pattern_node.parse(None) is None

    def test_list_pattern_node_parse_none_returns_none_unless_required(self, test_item):
        list_pattern_node = node.ListPatternNode(item=test_item, required=True)
        with pytest.raises(node.ValueNodeError):
            list_pattern_node.parse(None)

    def test_list_pattern_node_parse_none_returns_none_unless_default(self, test_item):
        list_pattern_node = node.ListPatternNode(item=test_item, default=('foo', 'bar'))
        list_value_node = list_pattern_node.parse(None)
        for parsed_item in list_value_node:
            assert parsed_item.value in ('foo', 'bar')


class TestDictPatternNode:

    valid_item_patterns = (
        {},
        tuple(),    # empty mapping
        [],         # same
        [('0', (('name', 'foo'), ('type', node.StringPatternNode)))],
        {'0': {'type': node.StringPatternNode, 'name': 'foo'}},
        {'0': (('type', node.StringPatternNode), ('name', 'foo'))},
        {'0': {'type': node.StringPatternNode, 'name': 'foo'}, '10': {'type': node.BooleanPatternNode, 'name': 'bar'}},
    )

    invalid_item_patterns = (
        None,
        'foo',
        {'0': None},  # no item
        {'0': {}},  # no type, no name
        {'0': {'name': 'foo'}},  # no type #2
        {'0': {'type': None, 'name': 'foo'}},  # invalid type #1
        {'0': {'type': 'ham', 'name': 'foo'}},  # invalid type #2
        {'0': {'type': str, 'name': 'foo'}},  # invalid type #3
        {'0': {'type': node.StringPatternNode}},  # no name
        {'0': {'type': node.StringPatternNode, 'Name': None}},  # None name
        {'0': {'type': node.StringPatternNode, 'name': []}},  # unhashable name
    )

    @pytest.fixture()
    def test_item(self):
        return {
            '10': {
                'type': node.StringPatternNode, 'name': 'foo', 'default': 'ham',
            },
            '20': {
                'type': node.NumericPatternNode, 'name': 'bar', 'default': '42',
            },
        }

    def test_dict_pattern_node_requires_items_keyword(self):
        with pytest.raises(node.PatternNodeError):
            node.DictPatternNode()

    def test_dict_pattern_node_accepts_items_as_positional_argument(self, test_item):
        pattern_node = node.DictPatternNode(test_item)
        assert isinstance(pattern_node.item('foo'), node.StringPatternNode)

    @pytest.mark.parametrize('invalid', invalid_item_patterns)
    def test_dict_pattern_fails_on_invalid_pattern_items(self, invalid):
        with pytest.raises(node.PatternNodeError):
            node.DictPatternNode(items=invalid)

    @pytest.mark.parametrize('invalid', invalid_item_patterns)
    def test_dict_pattern_fails_on_invalid_pattern_items_with_items_as_positional_arg(self, invalid):
        with pytest.raises(node.PatternNodeError):
            node.DictPatternNode(invalid)

    @pytest.mark.parametrize('valid', valid_item_patterns)
    def test_dict_pattern_passes_on_valid_pattern_items(self, valid):
        node.DictPatternNode(items=valid)

    @pytest.mark.parametrize('valid', valid_item_patterns)
    def test_dict_pattern_passes_on_valid_pattern_items_with_items_as_positional_arg(self, valid):
        node.DictPatternNode(valid)

    @pytest.mark.parametrize('valid', valid_item_patterns)
    def test_dict_pattern_items_are_subclasses_of_base_pattern_node(self, valid):
        dict_pattern_node = node.DictPatternNode(items=valid)
        assert len(dict_pattern_node.items) == len(valid)
        for pattern_item_key, pattern_item_value in dict_pattern_node.items.items():
            assert isinstance(pattern_item_value, node.BasePatternNode)

    @pytest.mark.parametrize('valid', [
        {'10': 'bar', '20': 42},
        {},
        (),  # empty mapping
        [],  # same
    ])
    def test_dict_pattern_parse_expects_valid_mapping(self, test_item, valid):
        dict_pattern_node = node.DictPatternNode(items=test_item)
        dict_pattern_value = dict_pattern_node.parse(valid)
        assert isinstance(dict_pattern_value, dict)
        assert isinstance(dict_pattern_value, node.BaseValueNode)
        assert len(dict_pattern_value) == len(test_item)

    @pytest.mark.parametrize('invalid', [
        'foo',
        0,
        False,
        (('foo', 'bar'), ('spam', 'eggs', '42')),  # invalid mapping
    ])
    def test_dict_pattern_parse_fails_on_invalid_mapping(self, test_item, invalid):
        dict_pattern_node = node.DictPatternNode(items=test_item)
        with pytest.raises(node.ValueNodeError):
            dict_pattern_node.parse(invalid)

    def test_dict_pattern_parse_none_returns_none(self, test_item):
        dict_pattern_node = node.DictPatternNode(items=test_item)
        assert dict_pattern_node.parse(None) is None

    def test_dict_pattern_parse_none_returns_none_unless_required(self, test_item):
        dict_pattern_node = node.DictPatternNode(items=test_item, required=True)
        with pytest.raises(node.ValueNodeError):
            dict_pattern_node.parse(None)

    def test_dict_pattern_parse_none_returns_none_unless_default(self, test_item):
        dict_pattern_node = node.DictPatternNode(items=test_item, default={'10': 'baz', '20': '42'})
        dict_value_node = dict_pattern_node.parse(None)
        assert dict_value_node is not None
        assert dict_value_node['foo'].value == 'baz'
        assert dict_value_node['bar'].value == 42

    def test_dict_pattern_parse_fails_on_extra_items(self, test_item):
        dict_pattern_node = node.DictPatternNode(items=test_item)
        with pytest.raises(node.ValueNodeError):
            dict_pattern_node.parse({'10': 'baz', '20': '42', 'extra_key': None})

    def test_dict_pattern_parse_fails_on_missing_items(self, test_item):
        test_item['20']['required'] = True

        dict_pattern_node = node.DictPatternNode(items=test_item)

        with pytest.raises(node.ValueNodeError):
            dict_pattern_node.parse({})  # 20 is required
        with pytest.raises(node.ValueNodeError):
            dict_pattern_node.parse({'10': 'baz'})  # same


class TestDictPatternNodeItemTraversal:
    test_pattern = {
        '0': {
            'type': node.DictPatternNode,
            'name': 'foo',
            'items': {
                '0': {
                    'name': 'bar',
                    'type': node.StringPatternNode,
                },
                '1': {
                    'name': 'baz',
                    'type': node.DictPatternNode,
                    'items': {
                        '0': {
                            'type': node.MappingPatternNode,
                            'name': 'spam',
                            'table': {}
                        },
                    },
                },
            },
        },
        '1': {
            'name': 'spam',
            'type': node.StringPatternNode,
        }
    }

    @pytest.fixture
    def pattern_node(self):
        return node.RootPatternNode(items=self.test_pattern)

    @pytest.mark.parametrize('good, node_class', [
        ('foo', node.DictPatternNode),
        ('spam', node.StringPatternNode),
        ('foo__bar', node.StringPatternNode),
        ('foo__baz__spam', node.MappingPatternNode),
    ])
    def test_dict_pattern_node_item_traversal(self, pattern_node, good, node_class):
        assert isinstance(pattern_node.item(good), node_class)

    @pytest.mark.parametrize('invalid', [
        None,
        1,
        True,
        tuple(),
        'foo__ham',
        'spam__bar',
        'bar__ham',
        'bar__spam',
        'foo__baz__ham',
    ])
    def test_dict_pattern_node_item_traversal_rases_exception(self, pattern_node, invalid):
        with pytest.raises(node.PatternNodeError):
            pattern_node.item(invalid)
