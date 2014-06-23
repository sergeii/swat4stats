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

* python3 *(using python2 is supported by highly disouraged)*
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

Streaming to swat4stats.com
===========================
This plain and simple guide will help you to get your server connected to `swat4stats.com <http://swat4stats.com/>`_ the SWAT 4 Stats Tracker.

1. Make sure your server is tracked by `gametracker.com <http://www.gametracker.com/search/swat4/>`_.

   .. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/stream_gt1.png

   If it's not tracked by gametracker then you have to add it `manually <http://www.gametracker.com/servers/>`_ to the gametracker server list (you have to be a registered user).

   .. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/stream_gt2.png

   If gametracker refuses to add the server stating it could not scan it, then please make sure you have installed `this mod <http://github.com/sergeii/swat-gs2>`_ and supplied the gametracker form a valid port value. 

     By default the GS2 mod listens on a +2 port (for a 10480 server the query port would be 10482) unless you set it explicitly with the Port property.

2. Make sure your server is picked up by `the stats tracker <http://swat4stats.com/servers/>`_.

     It usually takes up to an hour for the stats tracker to pick up a new gametracker tracked server.

   In case the server has not be picked by the stats tracker for quite a long time, you have to make sure the server listens to Gamespy Protocol 1 queries on a +1 port. For a 10480 server the GS1 port would be 10481, like so::

         [AMMod.AMServerQuery]
         ServerQueryListenPort=10481
         TestAllStats=False

   or if using the `swat-gs1 <https://github.com/sergeii/swat-gs1>`_ mod (the preferred way)::

         [AMMod.AMServerQuery]
         ServerQueryListenPort=0
         TestAllStats=False

         [GS1.Listener]
         Enabled=True

   Please note that ``AMMod.AMServerQuery`` is prone to errors as it does not comply with the `standard <http://int64.org/docs/gamestat-protocols/gamespy.html>`_. Populated servers (10+ players) have a chance to appear offline to `swat4stats.com <http://swat4stats.com/>`_ because ``AMServerQuery`` does incorrectly split packets of data.

   Using `swat-gs1 <https://github.com/sergeii/swat-gs1>`_ as a replacement to ``AMServerQuery`` is highly encouraged.

3. When both `gametracker <http://www.gametracker.com/search/swat4/>`_ and `swat4stats.com <http://swat4stats.com/servers/>`_ start displaying the server, you have to install the `swat-julia-tracker <https://github.com/sergeii/swat-julia-tracker>`_ package:

   a. Pick the `latest <https://github.com/sergeii/swat-julia-tracker/releases>`_ package version.

   b. Make sure to download the correct package version suitable to your game version:

      * swat-julia-tracker.X.Y.Z.swat4.tar.gz - Vanilla SWAT 4
      * swat-julia-tracker.X.Y.Z.swat4exp.tar.gz - SWAT 4: The Stetchkov Syndicate

   c. Install the package by copying the 4 .u files from a tar archive into your server's System directory::

        Utils.u
        HTTP.u
        Julia.u
        JuliaTracker.u

   d. Make sure ``Swat4DedicatedServer.ini`` looks similar::

        [Engine.GameEngine]
        EnableDevTools=False
        InitialMenuClass=SwatGui.SwatMainMenu
        ...
        ServerActors=AMMod.AMGameMod
        ...
        ServerActors=Utils.Package
        ServerActors=HTTP.Package
        ServerActors=Julia.Core
        ServerActors=JuliaTracker.Extension

        [Julia.Core]
        Enabled=True

        [JuliaTracker.Extension]
        Enabled=True
        URL=http://swat4stats.com/stream/
        Key=swat4stats
        Attempts=5
        Feedback=True
        Compatible=False

4. Start the server and finish a round.

   If you manage to find the finished round at the `game report <http://swat4stats.com/games/history/>`_ page, then the server has been successfully connected.

   .. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/stream_history.png

   In case you have not found any of the games played on the server at the `game report <http://swat4stats.com/games/history/>`_ page  within a reasonable amount of time (~10 min), then please carefully read the message displayed in admin chat upon a round end and attempt to fix the issue. If it does report nothing, then there is no streaming issues or you have not correctly installed the `swat-julia-tracker <https://github.com/sergeii/swat-julia-tracker>`_ package (step 3).

Feel free to contact me with either e-mail (kh.sergei@gmail.com) or xfire (`mytserge <http://classic.xfire.com/profile/mytserge/>`_).
