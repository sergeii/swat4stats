import collections.abc


class BaseNodeError(Exception):
    """Base node exception."""
    pass


class PatternNodeError(BaseNodeError):
    """Raise PatternNodeError if unable to construct a pattern node object."""
    pass


class ValueNodeError(BaseNodeError):
    """Raise ValueNodeError if unable to parse a raw value or construct a value node object."""
    pass


class BaseValueNode:

    def __init__(self, raw, pattern):
        self.raw = raw
        self.pattern = pattern
        self.value = None

    def __repr__(self):
        if self.value is not None:
            return repr(self.value)
        return super().__repr__()


class PrimitiveValueNode(BaseValueNode):
    """Use this class for primitive values such as a number or a string."""
    pass


class DictValueNode(BaseValueNode, dict):
    """A value node (subclass of BaseValueNode) class that makes its instances dict-like objects."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dict.__init__(self)


class ListValueNode(BaseValueNode, list):
    """A value node (subclass of BaseValueNode) class that makes its instances list-like objects."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        list.__init__(self)


class DefaultValueMixin:
    """
    A mixin that extends a pattern node class mro
    with the modified __init__ and parse methods:

    * __init__ takes an extra keyword argument "default"
    * parse replaces a None value with the default value.
    """

    def __init__(self, **kwargs):
        self.default = kwargs.pop('default', None)
        super().__init__(**kwargs)

    def parse(self, value):
        if value is None and self.default is not None:
            value = self.default
        return super().parse(value)


class RequiredValueMixin:
    """
    A mixin that extends a pattern node class mro
    with the modified __init__ and parse methods:

    * __init__ takes an extra keyword argument "required"
    * parse raises ValueNodeError if passed a None value
    """

    def __init__(self, **kwargs):
        self.required = bool(kwargs.pop('required', None))
        super().__init__(**kwargs)

    def parse(self, value):
        if value is None and self.required:
            node_name = getattr(self, 'name', None) or type(self)
            raise ValueNodeError(f'{node_name} requires a value')
        return super().parse(value)


class BasePatternNode:
    # the parse method will yield instances of value_class attribute
    value_class = PrimitiveValueNode

    def __init__(self, **kwargs):
        # BasePatternNode takes no kwargs
        if kwargs:
            attrs_str = ', '.join(kwargs)
            raise PatternNodeError(f'{type(self)} does not accept {attrs_str}')

    def parse(self, value):
        if value is None:
            return None
        obj = self.value_class(value, self)
        obj.value = self.clean(value) if value is not None else None
        return obj

    def clean(self, value):
        raise NotImplementedError()


class StringPatternNode(RequiredValueMixin, DefaultValueMixin, BasePatternNode):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def clean(self, value):
        # force unicode
        if not isinstance(value, str):
            try:
                value = value.decode('utf-8')
            # not a bytes obj
            except AttributeError:
                value = self.clean(repr(value))
        return value


class NumericPatternNode(RequiredValueMixin, DefaultValueMixin, BasePatternNode):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def clean(self, value):
        try:
            return int(value)
        except Exception:
            try:
                return float(value)
            except Exception:
                raise ValueNodeError(f'{value} is not a valid number')


class MappingPatternNode(RequiredValueMixin, DefaultValueMixin, BasePatternNode):

    def __init__(self, table=None, **kwargs):
        table = table if table is not None else kwargs.pop('table', None)
        try:
            self.table = dict(table)
        except (ValueError, TypeError):
            raise PatternNodeError(f'{table} is not a valid mapping type')
        super().__init__(**kwargs)

    def clean(self, value):
        try:
            return self.table[value]
        except (KeyError, TypeError):
            raise ValueNodeError(f'failed to map {value}')

    def reverse(self, value):
        keys = list(self.table.keys())
        values = list(self.table.values())
        result = []
        while True:
            try:
                i = values.index(value)
            except ValueError:
                break
            else:
                result.append(keys[i])
                keys.pop(i)
                values.pop(i)
        if not result:
            raise ValueNodeError(f'failed to reverse {value}')
        if len(result) == 1:
            return result[0]
        return result


class BooleanPatternNode(RequiredValueMixin, DefaultValueMixin, BasePatternNode):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def clean(self, value):
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            raise ValueNodeError(f'{value} is not a valid boolean value')


class ListPatternNode(RequiredValueMixin, DefaultValueMixin, BasePatternNode):
    value_class = ListValueNode

    def __init__(self, item=None, **kwargs):
        # allow a ListPatternNode to be instantiated with item as a positional argument
        item = item if item is not None else kwargs.pop('item', None)

        if item is None:
            raise PatternNodeError(f'{type(self)}.__init__ requires an item')

        super().__init__(**kwargs)
        # pop the item class
        pattern_type = item.pop('type', None)
        # attempt to instantiate it
        try:
            self.item = pattern_type(**item)
        except TypeError as e:
            raise PatternNodeError(str(e))
        if not isinstance(self.item, BasePatternNode):
            raise PatternNodeError(f'{pattern_type} is not BasePatternNode or a subclass of')

    def parse(self, value):
        value_obj = super().parse(value)

        if value_obj is not None:
            items = value_obj.raw
            # assume value is a dictionary with ignorable keys
            try:
                items = list(items.values())
            except AttributeError:
                pass
            # items must be an explicit list/tuple instance
            if not isinstance(items, (list, tuple)):
                raise ValueNodeError(f'{items} is not a valid list instance')
            for raw_item_value in items:
                try:
                    value_obj.append(self.item.parse(raw_item_value))
                except ValueNodeError as e:
                    if hasattr(self, 'name'):
                        raise ValueNodeError(f'{self.name}: {e}')
                    raise
        return value_obj

    def clean(self, value):
        return None


class DictPatternNode(RequiredValueMixin, DefaultValueMixin, BasePatternNode):
    value_class = DictValueNode

    def __init__(self, items=None, **kwargs):
        self.items = {}

        # allow a DictPatternNode to be instantiated with items as a positional argument
        items = items if items is not None else kwargs.pop('items', None)
        super().__init__(**kwargs)

        try:
            items = dict(items)
        except (ValueError, TypeError) as e:
            raise PatternNodeError(str(e))

        for key, value in items.items():
            try:
                item_options = dict(value)
            except (ValueError, TypeError) as e:
                raise PatternNodeError(str(e))

            item_type = item_options.pop('type', None)
            item_name = item_options.pop('name', None)

            # avoid None and unhashable names
            if item_name is None or not isinstance(item_name, collections.abc.Hashable):
                raise PatternNodeError(f'{item_name} is not valid dict item key')

            try:
                item_obj = item_type(**item_options)
            except TypeError as e:
                raise PatternNodeError(str(e))

            if not isinstance(item_obj, BasePatternNode):
                raise PatternNodeError(f'{item_type} is not BasePatternNode or a subclass of')

            setattr(item_obj, 'name', item_name)
            self.items[key] = item_obj

    def parse(self, value):
        value_obj = super().parse(value)

        if value_obj is not None:
            try:
                value_items = dict(value_obj.raw)
            except (ValueError, TypeError) as e:
                raise ValueNodeError(f'failed to parse {value_obj.raw} ({e})')

            for item_key, item in self.items.items():
                try:
                    value_obj[item.name] = item.parse(value_items.pop(item_key, None))
                except ValueNodeError as e:
                    raise ValueNodeError(f'{item.name}: {e}')

            # Unparsed items left
            if value_items:
                keys = ', '.join(list(value_items))
                raise ValueNodeError(f'the dict keys {keys} are not expected')
        return value_obj

    def clean(self, value):
        return None

    def item(self, name):
        try:
            components = name.split('__')
        except AttributeError:
            raise PatternNodeError(f'{name} is not a valid item name')
        node = self
        while components:
            component = components[0]
            try:
                values = list(node.items.values())
            # not a dict item
            except AttributeError:
                break
            for item in values:
                if item.name == component:
                    node = item
                    break
            else:
                break
            # shift the list
            components.pop(0)
        if components:
            raise PatternNodeError(f'failed to retrieve {name}')
        return node


class RootPatternNode(DictPatternNode):
    pass
