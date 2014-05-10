# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import os
from fabric.api import *

from . import deploy, secrets, backend, frontend, cache


env.always_use_pty = False
env.use_ssh_config = True

HERE = utils.mkpath(os.path.dirname(__file__))
BASE = utils.mkpath('/home/www_swat4tracker/')
PROJECT = BASE.child('app')

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
    'apps': ('tracker',),
    'uid': 'www_swat4tracker',
    'gid': 'www_swat4tracker',
    'python': utils.mkpath('/usr/bin/python3.4'),
}

env.project['dirs'] = (
    (BASE.child('pid'), None, '0777'),
    (BASE.child('log'), None, '0777'),
    # public dirs must be owned by the uwsgi user and readable by everyone
    ('/var/www/media/swat4tracker/', '%s:%s' % (env.project['uid'], env.project['gid']), '0755'),
    ('/var/www/static/swat4tracker/', '%s:%s' % (env.project['uid'], env.project['gid']), '0755'),
)

env.nginx = {
    # site name
    'name': env.project['name'],
    'conf': env.paths['conf'].child('nginx.conf'),
}

env.crontab = {
    'user': env.project['uid'],
    'conf': env.paths['conf'].child('crontab.txt'),
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