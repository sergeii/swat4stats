# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
from fabric.api import *

from . import deploy, secrets, backend, frontend, cache


env.always_use_pty = False
env.use_ssh_config = True

HERE = utils.mkpath(os.path.dirname(__file__))
BASE = utils.mkpath('/home/django/swat4tracker/')
PROJECT = BASE.child('src')

env.roledefs = {
    'backend': ['188.226.208.32'],
    'frontend': ['188.226.208.32'],
}

env.git = {
    'path': 'git@localhost:web/swat4tracker',
    'ref': 'origin/master',
}

env.paths = {
    'here': HERE,
    'base': BASE,
    'project': PROJECT,
    'conf': PROJECT.child('conf'),
}

env.project = {
    # also the uwsgi supervisorctl name
    'name': 'swat4tracker',
    'owner': 'django:django',
    'python': utils.mkpath('/usr/bin/python3'),
    # extra dirs to create
    'dirs': (
        (BASE.child('pid'), None, '0777'),
        (BASE.child('sock'), None, '0777'),
        (BASE.child('log'), None, '0777'),
        # public static folder
        (BASE.child('static'), None, None),
        # public media folder (nginx owned)
        (BASE.child('media'), 'www-data:www-data', None),
    )
}

env.nginx = {
    # site name
    'name': env.project['name'],
    'conf': env.paths['conf'].child('nginx.conf'),
}

env.uwsgi = {
    'ini': env.paths['conf'].child('uwsgi.ini'),
    'pidfile': env.paths['conf'].child('uwsgi.ini'),
    'binary': env.paths['base'].child('bin', 'uwsgi'),
    # supervisorctl program name
    'name': '%s_uwsgi' % env.project['name'],
    'conf': env.paths['conf'].child('supervisor.conf'),
}

env.secrets = {
    'local': HERE.ancestor(2).child('secrets.json'),
    'remote': BASE.child('secrets.json'),
}