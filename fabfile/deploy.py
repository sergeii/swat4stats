# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import *

from . import backend, frontend, cache


@task
def reload():
    execute(code)
    execute(dependencies)
    execute(contrib)
    execute(migrate)
    execute(invalidate)
    execute(collectstatic)
    execute(uwsgi)
    execute(celeryd)
    execute(celerybeat)
    execute(nginx)
    execute(crontab)


@task
def reinstall():
    """Reinstall everything from scratch."""
    execute(virtualenv)
    reload()


@task
@roles('backend')
def virtualenv():
    """Deploy virtualenv."""
    # rm -rf && virtualenv
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
def migrate_fake():
    for app in env.project['apps']:
        backend.managepy('migrate %s --fake' % app)


@task
@roles('backend')
def syncdb():
    backend.managepy('migrate --noinput')


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
def dependencies():
    """Install the python packages defined in requirements.txt."""
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
    frontend.supervisor_setup()
    frontend.supervisorctl('restart', env.uwsgi['name'])


@task
@roles('frontend')
def celeryd():
    """Deploy celery workers."""
    frontend.supervisor_setup()
    # control the whole group
    frontend.supervisorctl('restart', '%s:*' % env.celeryd['name'])


@task
@roles('frontend')
def celerybeat():
    """Deploy celery beat."""
    frontend.supervisor_setup()
    frontend.supervisorctl('restart', env.celerybeat['name'])

@task
@roles('backend')
def memcached():
    """Deploy memcached."""
    cache.memcached('restart')


# for backward compatibility..
@task
def everything():
    execute(reinstall)


@task
def restart():
    execute(reload)
