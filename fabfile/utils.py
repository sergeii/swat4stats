# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import json
from contextlib import contextmanager

from unipath import Path
from fabric.api import *
from fabric.contrib.console import confirm


def rmfiles(path, force=False):
    """Remove a directory contents upon a user confirmation."""
    if force or confirm("Do you really want to %s contents?" % path):
        puts("Purging %s contents." % path)
        sudo('rm -rf %s' % mkpath(path).child('*'))


def rmdir(path, force=False):
    """Remove a directory and it's contents upon a user confirmation."""
    if force or confirm("Do you really want to remove %s along with it's contents?" % path):
        puts("Purging %s and it's contents." % path)
        sudo('rm -rf %s' % path)


def mkdir(path, chown=None, chmod=None):
    """
    Create a directory.

    If either chown or chmod parameters are specified, alter the respective
    permissions onto the created directory.
    """
    sudo('mkdir -p %s' % path)
    if chown:
        sudo('chown %s %s' % (chown, path))
    if chmod:
        sudo('chmod %s %s' % (chmod, path))


def mkpath(path):
    """Return an instance of unipath.Path for the specified path."""
    return path if isinstance(path, Path) else Path(path)


def sudou(cmd, user):
    """Switch a user and run the specified command."""
    sudo(cmd, user=user)


def checkout(local, remote, ref='origin/master'):
    """
    Checkout the specified git revision on the local repository.

    If the local repository does not appear to be valid clone it from the
    specified remote source.
    """
    with quiet():
        if sudo('ls %s' % local).failed:
            sudo('git clone %s %s' % (remote, local))
    with cd(local):
        sudo('git fetch')
        sudo('git reset --hard %s' % ref)


@contextmanager
def virtualenv(path):
    """Activate a virtual environment."""
    with prefix('. %s' % mkpath(path).child('bin', 'activate')):
        yield


@contextmanager
def jsonable(path):
    """Return a writeable json object."""
    with open(path, 'a+') as handle:
        try: 
            obj = json.load(fp=handle)
        except:
            obj = {}
        finally:
            yield obj
    with open(path, 'w') as handle:
        json.dump(obj, fp=handle)