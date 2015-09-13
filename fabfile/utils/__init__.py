# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
import json
from functools import partial
from contextlib import contextmanager

from unipath import Path
from fabric.api import puts, sudo, cd, quiet, path
from fabric.contrib.console import confirm


def rmfiles(path, force=False):
    """Remove a directory contents upon a user confirmation."""
    if force or confirm('Do you really want to purge {} contents?'.format(path)):
        puts('purging {} contents'.format(path))
        sudo('rm -rf {}'.format(mkpath(path).child('*')))


def rmdir(path, force=False):
    """Remove a directory and it's contents upon a user confirmation."""
    if force or confirm('Do you really want to remove {}'.format(path)):
        puts('removing {}'.format(path))
        sudo('rm -rf {}'.format(path))


def mkdir(path, chown=None, chmod=None):
    """
    Create a directory.

    If either chown or chmod parameters are specified, alter the respective
    permissions onto the created directory.
    """
    sudo('mkdir -p {}'.format(path))
    if chown:
        sudo('chown {} {}'.format(chown, path))
    if chmod:
        sudo('chmod {} {}'.format(chmod, path))


def mkpath(path):
    """Return an instance of unipath.Path for the specified path."""
    return path if isinstance(path, Path) else Path(path)


def su(user):
    return partial(sudo, user=user)


@contextmanager
def virtualenv(virtualenv_path):
    with path(virtualenv_path, 'prepend'):
        yield


@contextmanager
def jsonable(path):
    """Return a writeable json object."""
    with open(path, 'a+') as handle:
        try:
            obj = json.load(fp=handle)
        except Exception:
            obj = {}
        finally:
            yield obj
    with open(path, 'w') as handle:
        json.dump(obj, fp=handle)
