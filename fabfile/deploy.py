# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import *

from . import backend, frontend, cache


@task
def restart():
    execute(code)
    execute(contrib)
    execute(migrate)
    execute(invalidate)
    execute(collectstatic)
    execute(uwsgi)
    execute(nginx)
    execute(crontab)


@task
def everything():
    """Deploy everything."""
    execute(project)
    execute(migrate)
    execute(invalidate)
    execute(collectstatic)
    execute(uwsgi)
    execute(nginx)
    execute(crontab)


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
def migrate():
    for app in env.project['apps']:
        backend.managepy('migrate %s' % app)


@task
@roles('backend')
def syncdb():
    backend.managepy('syncdb --noinput')


@task
@roles('backend')
def convert_to_south():
    for app in env.project['apps']:
        backend.managepy('migrate %s --fake' % app)


@task
@roles('backend')
def collectstatic():
    backend.managepy('collectstatic --noinput')
    backend.managepy('compress')


@task
@roles('backend')
def invalidate():
    backend.managepy('invalidate all')


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
@roles('backend')
def crontab():
    """Install cronjob for the user."""
    with quiet():
        sudo('crontab -r', user=env.crontab['user'])
    sudo('crontab %s' % env.crontab['conf'], user=env.crontab['user'])


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