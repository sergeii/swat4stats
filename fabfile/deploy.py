# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import *

from . import backend, frontend, cache

@task
def everything():
    """Deploy everything."""
    execute(project)
    execute(collectstatic)
    execute(uwsgi)
    execute(nginx)


@task
@roles('backend')
def base():
    """Deploy virtualenv."""
    backend.base()


@task
@roles('backend')
def code():
    """Deploy the project source code."""
    backend.checkout()

@task
@roles('backend')
def collectstatic():
    backend.managepy('collectstatic --noinput')


@task
@roles('backend')
def contrib():
    """Deploy additional application specific files."""
    put(env.secrets['local'], env.secrets['remote'], use_sudo=True)


@task
@roles('backend')
def project():
    """
    Deploy a backend environment along with the project source code.

    * Deploy a virtual environment
    * Deploy the application source code
    * Satisfy the application dependencies
    """
    backend.base()
    code()
    contrib()
    backend.dependencies()


@task
@roles('frontend')
def nginx():
    """Deploy an nginx site"""
    frontend.nginx_setup()
    frontend.nginx('restart')


@task
@roles('frontend')
def uwsgi():
    """Deploy a uwsgi server."""
    frontend.uwsgi_setup()
    frontend.supervisorctl('restart', env.uwsgi['name'])


@task
@roles('backend')
def memcached():
    """Deploy memcached."""
    cache.memcached('restart')