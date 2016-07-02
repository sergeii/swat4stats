# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

from . import definitions

# list pf case insensitive regex patterns used to describe a popular name
# in order to exclude it from a name isp profile lookup
POPULAR_NAMES = (
    r'^todosetname',
    r'^player',
    r'^newname',
    r'^afk',
    r'^giocatore',
    r'^jogador',
    r'^jugador',
    r'^joueur',
    r'^spieler',
    r'^gracz',
    r'^test',
    r'^\|\|$',
    r'^lol$',
    r'^swat$',
    r'^swat4$',
    r'^suspect$',
    r'^noob$',
    r'^n00b$',
    r'^vip$',
    r'^xxx$',
    r'^killer$',
    r'^david$',
    r'^pokemon$',
    r'^rambo$',
    r'^ghost$',
    r'^hitman$',
    r'^wolf$',
    r'^sniper$',
)

# a list of (url, regex pattern (for extracting ip and port)) tuples
# used by the tasks.update_server_list task to keep the server list up to date
SERVER_LIST_URLS = {
    # mark server list
    ('http://www.markmods.com/swat4serverlist/',
       r'\b(?P<addr>%s):(?P<port>%s)\b' % (definitions.PATTERN_IPV4, definitions.PATTERN_PORT)
    ),
    # gametracker/gsc server list
    ('http://api.getgsc.com/?command=get_gameservers_csv&search_by=game_abbrev&search_term=swat4&limit=1000',
        r'^(?P<addr>%s),(?P<port>%s)\b' % (definitions.PATTERN_IPV4, definitions.PATTERN_PORT)
    ),
}

# max number of concurrent server status requests
MAX_STATUS_CONNECTIONS = 50
