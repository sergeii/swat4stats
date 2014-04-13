# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import *

from . import utils


@task
def checkout():
    """
    Deploy the application source code.

    * Checkout the specified git revision of the repository cloned from the specified
      location into the application directory.
    """
    utils.checkout(env.paths['project'], env.git['path'], env.git['ref'])


@task
def base():
    """
    Deploy a base ala virtual environment for the application.

    * Wipe out the contents of the previous virtualenv residing on the same path
    * Create a virtual environment with the specified python binary
    * Create extra sub directories under the base directory
    """
    with quiet():
        # wipe out an existing virtualenv
        rmvirtualenv(force=True)
        # create a new virtualenv
    mkvirtualenv(python=env.project['python'])
    # create additional directories
    for (directory, chown, chmod) in env.project['dirs']:
        utils.mkdir(directory, chown, chmod)


@task 
def dependencies():
    """
    Satisfy Python package dependecies.

    * Upgrade pip itself
    * Upgrade the packages specified in the project's requirements.txt file
    """
    pip('install --quiet -U pip')
    pip('install --quiet -r %s' % env.paths['project'].child('requirements.txt'))


@task
def managepy(cmd):
    """Run a django's project manage.py command inside the virtual environment."""
    with utils.virtualenv(env.paths['base']):
        with cd(env.paths['project']):
            sudo('python %s %s' % (env.paths['project'].child('manage.py'), cmd))


@task
def pip(cmd, binary=None):
    """Issue a pip command inside the virtual environment."""
    sudo('%s %s' % (binary or env.paths['base'].child('bin', 'pip'), cmd))


@task
def mkvirtualenv(path=None, python=None):
    """Create a virtual environment."""
    opts = ['--no-site-packages']
    if python:
        opts.append('--python %s' % python)
    sudo('virtualenv %s -- %s' % (' '.join(opts), path or env.paths['base']))


@task
def rmvirtualenv(path=None, force=False):
    """
    Remove a virtual environment.

    This task is an alias to the rm -rf command.
    """
    utils.rmdir(path or env.paths['base'], force)