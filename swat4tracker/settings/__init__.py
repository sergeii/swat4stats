# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
import json

if 'DJ_LOCAL' in os.environ:
    from . local import *
elif 'DJ_DEBUG' in os.environ:
    from .debug import *
else:
    from .production import *

# update the namespace with the private settings
with open(PATH_VENV.child('secrets.json')) as handle:
    globals().update(**json.load(handle))