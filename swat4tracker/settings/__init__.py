# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
import json


DEBUG = 'DJ_DEBUG' in os.environ
TEMPLATE_DEBUG = DEBUG

if DEBUG:
    from .debug import *
else:
    from .production import *

# update the namespace with the private settings
with open(PATH_VENV.child('secrets.json')) as handle:
    globals().update(**json.load(handle))