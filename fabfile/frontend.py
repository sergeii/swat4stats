# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import *

from . import utils


def supervisorctl(cmd, name=None):
    """
    Issue a supervisorctl command.

    If program name if provided, use it as the second argument.
    """
    sudo('supervisorctl %s %s' % (cmd, name if name else ''))


@task
def nginx(cmd):
    """Issue an init.d command onto nginx."""
    sudo('service nginx %s' % cmd)


@task
def uwsgi(cmd, name=None):
    """Issue a supervisor supervisorctl command upon the uwsgi."""
    name = name or env.project['name']
    supervisorctl(cmd, name)


@task
def uwsgi_pip(cmd=None, binary=None, pidfile=None, ini=None):
    """
    Emit a uwsgi signal.

    If no cmd is provided, attempt to start the server.
    """
    pidfile = pidfile or env.uwsgi['pidfile']
    binary = binary or env.uwsgi['binary']

    with utils.virtualenv(env.paths['base']):
        with cd(env.paths['project']):
            # bin/uwsgi --reload /tmp/pidfile.pid
            if cmd:
                sudo('%s --%s %s' % (binary, cmd, pidfile))
            else:
                sudo('%s --ini %s --pidfile %s' % (binary, env.uwsgi['ini'], pidfile))


@task 
def nginx_setup():
    """
    Set up an nginx virtual server.
    
    * Copy the nginx server configuration file into /etc/nginx/sites-available
    * Enable the virtual host by symlinking the copied file from /etc/nginx/sites-available
      to /etc/nginx/sites-enabled
    """
    site_dir = utils.mkpath('/etc/nginx/')
    site_available = site_dir.child('sites-available', env.nginx['name'])
    site_enabled = site_dir.child('sites-enabled', env.nginx['name'])
    # xxx.conf to /etc/nginx/sites-available/xxx.conf
    sudo('cp %s %s' % (env.nginx['conf'], site_available))
    # /etc/nginx/sites-available/xxx.conf -> /etc/nginx/sites-enabled/xxx.conf
    sudo('ln -sf %s %s' % (site_available, site_enabled))


@task 
def supervisor_setup():
    """Set up supervisor."""
    # copy the conf file
    sudo('cp %s /etc/supervisor/conf.d/%s.conf' % (env.supervisor['conf'], env.project['name']))
    # reload
    supervisorctl('reread')
    supervisorctl('update')
