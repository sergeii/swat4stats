# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
from functools import partial, wraps
from contextlib import contextmanager

from fabric.contrib.files import exists
from fabric.api import (env, task, execute, roles, shell_env,
                        cd, sudo, quiet, path, puts, settings)

from .utils import su, rmdir, mkpath, virtualenv


class App(object):
    env_vars = {
        'DJ_PRODUCTION': '1',
        'DJ_SECRET_KEY': 'secret',
    }

    git = 'git@localhost:web/swat4tracker#origin/master'

    base = mkpath('/home/www_swat4tracker/')
    src = base.child('src')
    env = base.child('env')

    uwsgi_program = 'swat4tracker_uwsgi'
    celeryd_program = 'swat4tracker_celeryd:*'
    celerybeat_program = 'swat4tracker_celerybeat'

    user = 'www_swat4tracker'
    group = 'www_swat4tracker'
    python = '/usr/bin/python3.4'

    @property
    def git_path(self):
        return self.git.split('#', 1)[0]

    @property
    def git_ref(self):
        return self.git.split('#', 1)[-1]

    @contextmanager
    def cd(self):
        with cd(self.src):
            yield

    @contextmanager
    def activate(self):
        with self.cd():
            with virtualenv(self.env.child('bin')):
                with shell_env(**self.env_vars):
                    yield


app = App()
run = su(app.user)
pyenv = partial(path, '/usr/local/bin', 'prepend')
exists = partial(exists, use_sudo=True)


@task
def deploy():
    """Pull code updates from repo then deploy it"""
    execute(deploy_code)
    execute(mkvirtualenv)
    execute(install_requirements)
    execute(migrate)
    execute(invalidate)
    execute(collectstatic)
    restart()


@task
def restart():
    """Restart uwsgi and celery workers"""
    execute(uwsgi, 'restart')
    execute(celeryd, 'restart')
    execute(celerybeat, 'restart')


@task
@roles('backend')
def deploy_code():
    """Checkout code from git repo"""
    if not exists(app.src):
        puts('{} does not exist'.format(app.src))
        run('git clone {} {}'.format(app.git_path, app.src))
    with cd(app.src):
        run('git fetch')
        run('git reset --hard {}'.format(app.git_ref))
        run('git clean -fdx')


@task
@roles('backend')
def migrate(fake=False):
    """Apply apps migrations"""
    cmd = 'migrate'
    if fake:
        cmd = '{} --fake'.format(cmd)
    managepy(cmd)


@task
@roles('backend')
def collectstatic():
    managepy('collectstatic --noinput')
    managepy('compress')


@task
@roles('backend')
def invalidate():
    """Invalidate cachops cache"""
    managepy('invalidate all')


@task
@roles('backend')
def install_requirements():
    """
    Satisfy project dependencies:

        * Upgrade pip itself
        * Upgrade the packages specified in requirements.txt

    """
    with app.activate():
        run('pip install -r {}'.format(app.src.child('pip.txt')))
        run('pip install -r {}'.format(app.src.child('requirements.txt')))


@task
@roles('backend')
def nginx(cmd):
    sudo('service nginx {}'.format(cmd))


@task
@roles('backend')
def uwsgi(cmd):
    supervisorctl(cmd, app.uwsgi_program)


@task
@roles('backend')
def celeryd(cmd):
    supervisorctl(cmd, app.celeryd_program)


@task
@roles('backend')
def celerybeat(cmd):
    supervisorctl(cmd, app.celerybeat_program)


@task
@roles('backend')
def mkvirtualenv(recreate=False):
    """Create a virtual environment."""
    if exists(app.env):
        if not recreate:
            puts('{} already exists!'.format(app.env))
            return
        rmdir(app.env)
    opts = ['--no-site-packages', '--python {}'.format(app.python)]
    with pyenv():
        run('virtualenv {} -- {}'.format(' '.join(opts), app.env))


@task
def managepy(cmd):
    """Run a manage.py command"""
    with app.activate():
        run('python manage.py {}'.format(cmd))


@task
def supervisorctl(command, program=None):
    """Issue a supervisorctl command"""
    cmd = 'supervisorctl {}'.format(command)
    if program:
        cmd = '{} {}'.format(cmd, program)
    sudo(cmd)
