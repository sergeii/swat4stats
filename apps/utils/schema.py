from voluptuous import Invalid, Optional


class Mapping:
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, value):
        try:
            return self.mapping[value]
        except KeyError:
            exc_msg = f'"{value}" is not expected among {list(self.mapping)}'
            raise Invalid(exc_msg)


class OptionalMapping(Optional):
    def __init__(self, mapping, *args, **kwargs):
        default_key, _ = mapping.copy().popitem()
        self.mapping = mapping
        super().__init__(default_key, *args, **kwargs)

    def __call__(self, value):
        try:
            return self.mapping[value]
        except KeyError:
            exc_msg = f'"{value}" is not expected among {list(self.mapping)}'
            raise Invalid(exc_msg)


class FallbackMapping(Mapping):
    def __call__(self, value):
        try:
            return self.mapping[value]
        except KeyError:
            return value


class DefaultMapping(Mapping):
    def __init__(self, *args, **kwargs):
        self.default = kwargs.pop("default")
        super().__init__(*args, **kwargs)

    def __call__(self, value):
        try:
            return self.mapping[value]
        except KeyError:
            return self.default
