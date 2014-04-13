# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)


class StreamSourceValidationError(Exception):
    """Raise when stream data does not satisfy any of the registered servers."""
    pass