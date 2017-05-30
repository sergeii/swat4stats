# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
from functools import partial
from contextlib import contextmanager

from fabric.contrib.files import exists
from fabric.api import (env, task, execute, roles, shell_env,
                        cd, sudo, quiet, path, puts, settings)

from .utils import su, rmdir, mkpath, virtualenv


class App(object):
    env_vars = {
        'DJ_PRODUCTION': '1',
    }

    git = 'git@git.swat4stats.com:swat4stats/swat4stats#origin/master'

    base = mkpath('/home/swat4stats')
    src = base.child('src')
    env = base.child('env')

    local_static = base.child('static')
    remote_static = 'front.int.swat4stats.com::swat4stats'

    uwsgi_profile = 'swat4stats'
    celery_program = 'celery:'
    celerybeat_program = 'celerybeat'

    user = 'swat4stats'
    group = 'swat4stats'

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
pyenv = partial(path, '/opt/python3.4.4/bin', 'prepend')
exists = partial(exists, use_sudo=True)


@task
def deploy():
    execute(deploy_code)
    execute(deploy_env)
    execute(migrate)
    execute(invalidate)
    execute(deploy_static)
    execute(restart)


@task
def restart():
    execute(uwsgi, 'reload')
    execute(celerybeat, 'restart')
    execute(celery, 'restart')


@task
@roles('backend')
def reload():
    uwsgi('reload')


@task
@roles('backend')
def deploy_code():
    if not exists(app.src):
        puts('{} does not exist'.format(app.src))
        run('git clone {} {}'.format(app.git_path, app.src))
    with cd(app.src):
        run('git fetch')
        run('git reset --hard {}'.format(app.git_ref))
        run('git clean -fdx -e node_modules')


@task
@roles('backend')
def migrate(fake=False):
    cmd = 'migrate'
    if fake:
        cmd = '{} --fake'.format(cmd)
    managepy(cmd)


@task
@roles('backend')
def deploy_static():
    managepy('collectstatic --noinput')
    managepy('compress')
    run('rsync -a --delete {}/ {}/'.format(app.local_static, app.remote_static))


@task
@roles('backend')
def invalidate():
    managepy('invalidate all')


@task
@roles('backend')
def uwsgi(cmd):
    sudo('/etc/init.d/uwsgi {} {}'.format(cmd, app.uwsgi_profile))


@task
@roles('backend')
def celery(cmd):
    supervisorctl(cmd, app.celery_program)


@task
@roles('backend')
def celerybeat(cmd):
    supervisorctl(cmd, app.celerybeat_program)


@task
@roles('backend')
def deploy_env(recreate=False):
    env_exists = exists(app.env)

    if env_exists:
        puts('{} already exists'.format(app.env))
        if recreate:
            puts('removing {}'.format(app.env))
            rmdir(app.env)
            env_exists = False

    if not env_exists:
        with pyenv():
            run('virtualenv {}'.format(app.env))

    with app.activate():
        run('pip install pip --upgrade')
        run('pip install -r {} --exists-action=w'.format(app.src.child('requirements.txt')))

    with app.cd():
        run('npm install')


@task
def managepy(cmd):
    with app.activate():
        run('python manage.py {}'.format(cmd))


@task
def supervisorctl(command, program=None):
    cmd = 'supervisorctl {}'.format(command)
    if program:
        cmd = '{} {}'.format(cmd, program)
    sudo(cmd)
