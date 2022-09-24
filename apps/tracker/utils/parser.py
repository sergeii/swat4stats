import re
from urllib.parse import unquote_to_bytes, unquote_plus


class JuliaQueryString(dict):

    def parse(self, query_string):
        """
        Parse a raw querystring and set the parsed items as members of the instance.
        Do not let duplicate keys to shadow the same keys that have been set previously.
        Instead turn the item into a list of concurrent values.

        Example:
            >>> qs = QueryString()
            >>> qs.parse('field=value')
            >>> assert qs == {'field': 'value'}

            >>> qs = QueryString()
            >>> qs.parse('foo=bar&foo=ham&foo=baz')
            >>> assert qs == {'foo': ['bar', 'ham', 'baz']}
        """
        for param_name, param_value in self.parse_querystring(query_string):
            # skip empty keys
            if not param_name:
                continue
            try:
                self[param_name]
            except KeyError:
                # the key has not yet been occupied
                self[param_name] = param_value
            else:
                # the key has already been occupied
                try:
                    # assume it has already been converted to a list
                    self[param_name].append(param_value)
                except AttributeError:
                    # convert the exisiting value to a list
                    self[param_name] = [self[param_name], param_value]
        return self

    def expand_dots(self):
        """
        Turn a dot separated key into an n-dimensinal structure.

        Example:
            >>> qs = QueryString()
            >>> qs.parse('foo.bar=ham')
            >>> qs.expand_dots()
            >>> assert qs == {'foo': {'bar': 'ham'}}

            >>> qs = QueryString()
            >>> qs.parse('foo.bar.baz=ham&foo.bar.spam=eggs&foo.bar.spam=42')
            >>> qs.expand_dots()
            >>> assert qs == {'foo': {'bar': {'baz': 'ham', 'spam': 'eggs'}, 'spam': '42'}
        """
        # iterate a copy of the keys to keep the iteration intact
        dict_keys = list(self.keys())
        for dict_key in dict_keys:
            dict_value = self[dict_key]
            # delete the original item
            del self[dict_key]
            # split param name with a string and filter out empty components
            key_components = list(filter(None, [x.strip() for x in dict_key.split('.')]))
            # dont proceed if the key is component-less
            if key_components:
                self.set_complex_key_item(self, key_components, dict_value)
        return self

    def expand_array(self):
        pattern = re.compile(
            r'^(?P<key>[^\[\]]+)(?P<dictkeys>(?:\[[^\[]+\])+)?(?P<listkey>\[\])?$'
        )
        # iterate a copy of the keys
        dict_keys = list(self.keys())
        for dict_key in dict_keys:
            dict_value = self[dict_key]
            # delete the original item
            del self[dict_key]
            # attempt to match the key name against the uri array pattern
            matched = re.match(pattern, dict_key)
            if matched:
                key_components = [matched.group('key')]
                # if found, concatenate the subkeys into a list along with the primary parameter key
                if matched.group('dictkeys'):
                    key_components.extend(matched.group('dictkeys')[1:-1].split(']['))
                # convert a non list value to a list element
                try:
                    dict_value.append
                except AttributeError:
                    dict_value = [dict_value]
                # append each value from the list to the deepest item
                for value in dict_value:
                    # if the explicit listkey token is present ("[]"),
                    # wrap the value into a list
                    if matched.group('listkey'):
                        value = [value]
                    self.set_complex_key_item(self, key_components, value)
        return self

    @staticmethod
    def set_complex_key_item(initial_dict, key_components, value):
        # dont modify the original components list
        key_components = list(key_components)
        # append nested dictionaries to the initial dict
        nested_dict = initial_dict
        # ..except for the final item
        last_key_component = key_components.pop()
        # traverse further deep into the nested structure
        for key in key_components:
            # if the key had existed prior to the lookup and the item is not a dict,
            # replace it with an empty dict
            if not isinstance(nested_dict.get(key, None), dict):
                nested_dict[key] = {}
            nested_dict = nested_dict[key]
        # when encountered an existing item with the key in question,
        # treat it like a list
        # e.g. field=foo&field=bar turns into a dict item mapping the
        # occupied key to a list of the conflicting values:
        # {'field': ['foo', 'bar']}
        try:
            # if the value is a mutable sequence itself, attempt to extend the existing list
            value.append
        except AttributeError:
            # if it is not, then append the value
            method = 'append'
        else:
            method = 'extend'
        # attempt to set the value..
        try:
            # ..to an existing list
            getattr(nested_dict[last_key_component], method)(value)
        except AttributeError:
            # ..to an occupied non-list item..
            if not isinstance(nested_dict[last_key_component], dict):
                # ..unless its an existing dict
                nested_dict[last_key_component] = [nested_dict[last_key_component], value]
        except KeyError:
            # ..to a nonexistent item
            nested_dict[last_key_component] = value

    @staticmethod
    def parse_querystring(query_string):
        """
        Parse a raw query string.

        Args:
            query_string: raw query string

        Return a list of 2-tuples (key=value).

        Examples:
            >>> parsed = QueryString.parse_querystring('field1=foo&field2=bar')
            >>> expected = [('field1', 'foo'), ('field2', 'bar')]
            >>> parsed == expected
            True
        """
        result = []
        # make sure the string neither begins nor ends with a &
        # the same rule applies to query parameters split by a =
        # ie filter out &field&, =field, field=, =field=value, etc
        for param in query_string.strip('&').split('&'):
            param_split = param.strip('=').split('=', 1)  # max_splits=1
            result.append(tuple([
                unquote_plus(unquote_to_bytes(x.encode('utf-8')).decode('utf-8'))  # 2/3 hack
                for x in (param_split + [''])[:2]  # make sure the param value is present
            ]))
        return result
