SWAT 4 Stats Tracker
%%%%%%%%%%%%%%%%%%%%

SWAT 4 stats tracker source code http://swat4stats.com/

.. image:: https://requires.io/github/sergeii/swat4stats.com/requirements.png?branch=master
     :target: https://requires.io/github/sergeii/swat4stats.com/requirements/?branch=master
     :alt: Requirements Status

Features
========

Original SWAT 4 Interface
^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/main.png


Leaderboard
^^^^^^^^^^^

.. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/leaderboard.png


Game Reports
^^^^^^^^^^^^

.. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/game.png


Real-time Server Stats
^^^^^^^^^^^^^^^^^^^^^^

.. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/servers.png


Detailed Player Stats
^^^^^^^^^^^^^^^^^^^^^

.. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/profile.png

.. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/profile2.png


Deployment
==========

Prerequisites:

* python3
* PostgreSQL
* redis
* `CoffeeScript <http://coffeescript.org/>`_
* `Less <http://lesscss.org/>`_ 
* `Fabric <http://www.fabfile.org/>`_


Configure `SECRET_KEY`::

    $ fab secrets.make
    Please enter a secret name:
    $ SECRET_KEY
    Please enter the secret value
    $ secret

Configure redis settings to suit your environment::
    
    # swat4tracker/settings/local.py

    CACHES['default'] = {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': '127.0.0.1:6379:1',
    }

    CACHEOPS_REDIS = {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 2,
        'socket_timeout': 3,
    }

Configure PostgreSQL::

    CREATE ROLE swat4tracker WITH CREATEDB LOGIN ENCRYPTED PASSWORD 'swat4tracker';
    CREATE DATABASE swat4tracker WITH OWNER swat4tracker;

Setup virtual environment::

    virtualenv --python=`which python3` /tmp/swat4stats
    source /tmp/swat4stats/bin/activate
    git clone https://github.com/sergeii/swat4stats.com /tmp/swat4stats/code
    cd /tmp/swat4stats/code
    pip install -r requiremets.txt

Migrate db::

    DJ_DEBUG=1 ./manage.py syncdb
    DJ_DEBUG=1 ./manage.py migrate

Run server with the local settings `swat4tracker.settings.debug`::

    DJ_DEBUG=1 ./manage.py runserver

Fetch servers from gametracker and markmods::
    
    DJ_DEBUG=1 ./manage.py cron_fetch_servers

Query servers every 10 seconds for 10 minutes::

    DJ_DEBUG=1 ./manage.py cron_query_servers 600 10

Required Streaming Software
===========================
* `swat-utils <https://github.com/sergeii/swat-utils>`_
* `swat-http <https://github.com/sergeii/swat-http>`_
* `swat-julia <https://github.com/sergeii/swat-julia>`_
* `swat-julia-tracker <https://github.com/sergeii/swat-julia-tracker>`_
