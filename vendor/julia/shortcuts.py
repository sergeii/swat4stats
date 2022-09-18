import copy

from . import node, parse


def parse_pattern(pattern):
    return node.RootPatternNode(items=copy.deepcopy(pattern))


def julia_v1(query_string):
    """
    Parse a raw query string formed with Julia 1.x

    Args:
        query_string: Raw query string in the format of
        key1=value2&key2=value2&key3[subkey1]=value3&key3[subkey2]=value4

    Return a QueryString dict-like instance

    Examples:
        >>> parsed = julia_v2('foo[bar]=ham&foo[bar]=baz&foo[spam]=eggs')
        >>> expected = {'foo': {'bar': ['ham', 'baz'], 'spam': 'eggs'}}
        >>> assert parsed == expected
    """
    return parse.QueryString().parse(query_string).expand_array()


def julia_v2(query_string):
    """
    Parse a raw query string formed with the Julia 2.x Tracker extension,
    where nested structure keys are delimited with a dot instead of the usual
    uri array bracket notation.

    Args:
        query_string: Raw query string in the format of
        key1=value2&key2=value2&key3.subkey1=value3&key3.subkey2=value4

    Return a QueryString dict-like instance with dots expanded

    Examples:
        >>> parsed = julia_v2('foo.bar=ham&foo.bar=baz&foo.spam=eggs')
        >>> expected = {'foo': {'bar': ['ham', 'baz'], 'spam': 'eggs'}}
        >>> assert parsed == expected
    """
    return parse.QueryString().parse(query_string).expand_dots()


def map(pattern, name, value, method_name='clean', coerce=None):
    # parse pattern dict
    if not isinstance(pattern, node.DictPatternNode):
        pattern = node.DictPatternNode(items=pattern)
    # get the specified child item
    item = pattern.item(name)
    if not isinstance(item, node.MappingPatternNode):
        raise node.ValueNodeError(f'{name} is not a MappingPatternNode instance')
    # forward/backward
    method = getattr(item, method_name)
    # attempt return a singleton value
    if not isinstance(value, (tuple, list)):
        value = method(value)
        if coerce:
            # coerce the elements of the container
            if isinstance(value, (tuple, list)):
                value = type(value)(coerce(nested_value) for nested_value in value)
            else:
                value = coerce(value)
        return value
    mapped = []
    for nested_value in value:
        nested_value = map(pattern, name, nested_value, method_name, coerce)
        # multiple values have been returned
        if isinstance(nested_value, (tuple, list)):
            mapped.extend(nested_value)
        else:
            mapped.append(nested_value)
    # return a sequence of mapped values of the same type as the original sequence
    return type(value)(mapped)


def unmap(pattern, name, value, **kwargs):
    return map(pattern, name, value, method_name='reverse', **kwargs)
