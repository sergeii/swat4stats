# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import *

@task
def memcached(cmd):
    """Issue an init.d command onto memcached."""
    sudo('service memcached %s' % cmd)