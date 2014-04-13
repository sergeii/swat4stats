# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import six
from fabric.api import *

from . import utils

@task(default=True)
def show():
    """List the current secrets."""
    puts('Available secrets:')
    with utils.jsonable(env.secrets['local']) as obj:
        for key, value in six.iteritems(obj):
            puts('%s:%s' % (key, value))

@task
def make(**kwargs):
    """Create new or update existing secrets."""
    if not kwargs:
        kwargs = {}
        while True:
            secret = prompt('Please enter a secret name:').strip()
            if secret:
                kwargs[secret] = prompt('Please enter the secret value:').strip()
                if prompt('Would you like to continue?', default='y').lower() in ('n', 'no'):
                    break
            else:
                if prompt('Would you like to abandon?', default='y').lower() in ('y', 'yes'):
                    break
    if kwargs:
        with utils.jsonable(env.secrets['local']) as obj:
            obj.update(**kwargs)
            puts('Updated the following secrets: %s' % ', '.join(list(kwargs.keys())))

@task
def remove(*args, **kwargs):
    """Remove items from the secrets dictionary."""
    force = kwargs.pop('force', False)
    if force or prompt('Do you really want to remove %s?' % ', '.join(args), default='n') in ('y', 'yes'):
        with utils.jsonable(env.secrets['local']) as obj:
            for key in args:
                puts('Removing %s' % key)
                del obj[key]

@task
def wipeout():
    """Clear the secrets dectionary."""
    with utils.jsonable(env.secrets['local']) as obj:
        keys = list(obj.keys())
    if keys:
        remove(*keys)
