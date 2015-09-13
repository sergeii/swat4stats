# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os


if 'DJ_PRODUCTION' in os.environ:
    from .production import *
elif 'DJ_DEBUG' in os.environ:
    from .debug import *
else:
    from .local import *
