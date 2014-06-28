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

.. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/games.png

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

* python2.7, python3.3, python3.4
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

API
===
`swat4stats.com <http://swat4stats.com/>`_ provides API for the following services:


* `swat-motd <https://github.com/sergeii/swat-motd>`_

  * weekly/monthly summary - displays summary stats

      .. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/api_summary.png

    To display summary you have to configure `swat-motd <https://github.com/sergeii/swat-motd>`_ the following way::

        [MOTD.Core]
        Enabled=True
        URL=http://swat4stats.com/api/motd/summary/

    By default summary will be displayed in 60 seconds after a map start. Summary is displayed line by line with a delay of 1 second.

    To configure the way summary is displayed, use the following parameters:

    * **initial** controls the time (in seconds) after a map start summary is displayed (defaults to 60 seconds)
    * **repeat** controls interval (in seconds) between repetitions (defaults to 0, i.e. no repetition)
    * **delay**/**nodelay** controls whether summary lines are displayed with a 1 second delay or instantly (defaults to delay)

    Example:

    Display summary with no delay::

      URL=http://swat4stats.com/api/motd/summary/?nodelay

    Display summary in 5 minutes after a map start::
      
      URL=http://swat4stats.com/api/motd/summary/?initial=300

    Display summary in 2 minutes after a map start, then keep repeating the message every 10 minutes::

      URL=http://swat4stats.com/api/motd/summary/?initial=120&repeat=600

  * leaderboard - display top 5 players of the year from a specific leaderboard

      .. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/api_leaderboard.png

    The leadeboard API url has the following format::

      http://swat4stats.com/api/motd/leaderboard/<leaderboard>/

    where ``<leaderboard>`` may be any of the following::

      score
      time
      wins
      spm
      top_score
      kills
      arrests
      kdr
      ammo_accuracy
      kill_streak
      arrest_streak
      vip_escapes
      vip_rescues
      vip_captures
      vip_kills_valid
      coop_score
      coop_time
      coop_games
      coop_wins
      coop_enemy_arrests
      coop_enemy_kills

    The parameters ``initial``, ``repeat``, ``delay`` and ``nodelay`` (described above) are also available.

    Example:

    Display random leaderboard::
     
      URL=http://swat4stats.com/api/motd/leaderboard/

    Display score leaderboard every 5 minutes::
      
      URL=http://swat4stats.com/api/motd/leaderboard/score/?repeat=300

    Display CO-OP score leaderboard every 10 minutes starting 10 minutes after a map launch::
      
      URL=http://swat4stats.com/api/motd/leaderboard/coop_score/?initial=600&repeat=600

    Display top 5 players by k/d ratio every 10 minutes (no delay)::

      URL=http://swat4stats.com/api/motd/leaderboard/kill_streak/?repeat=600&nodelay

    Display top 5 players by kills and arrests in 3 and 6 minutes respectively after a map start (no repetition)::

      URL=http://swat4stats.com/api/motd/leaderboard/kills/?initial=180
      URL=http://swat4stats.com/api/motd/leaderboard/arrests/?initial=360

* `swat-julia-whois <https://github.com/sergeii/swat-julia-whois>`_

  `swat4stats.com <http://swat4stats.com>`_ may be used as a source for a ``!whois`` command response.

     .. image:: https://raw.githubusercontent.com/sergeii/swat4stats.com/master/docs/screenshots/api_whois.png

  In order to use `swat4stats.com <http://swat4stats.com>`_ as a ``!whois`` command source you must to connect the server to the stats tracker. Then configure `swat-julia-whois <https://github.com/sergeii/swat-julia-whois>`_ the following way::

     [JuliaWhois.Extension]
     Enabled=True
     URL=http://swat4stats.com/api/whois/
     Key=swat4stats
     Auto=True
