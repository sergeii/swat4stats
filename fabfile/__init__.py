# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import env, cd, shell_env

from .deploy import *  # noqa


env.always_use_pty = False
env.use_ssh_config = True
env.roledefs = {
    'backend': ['swat4stats.jodie'],
}
env.sudo_prefix += '-i'
