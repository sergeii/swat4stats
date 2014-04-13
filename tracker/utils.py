# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import, division)

import re
import hashlib
import logging

import six

from django.core.urlresolvers import reverse
from django.utils.encoding import force_bytes, force_text
from django.db import connection

from . import definitions

logger = logging.getLogger(__name__)


class lock(object):
    """
    Context manager for aquiring a transaction-wide lock on PostgreSQL tables.

    The __init__ method accepts two or more arguments. 

    The first argument is always a LOCK mode from the list of the standard lock names
        ACCESS SHARE
        ROW SHARE
        ROW EXCLUSIVE
        SHARE UPDATE EXCLUSIVE
        SHARE
        SHARE ROW EXCLUSIVE
        EXCLUSIVE
        ACCESS EXCLUSIVE

    The subsequent args are models that require a lock.
    """
    def __init__(self, mode, *models):
        self.mode = mode
        self.models = models
        self.tables = []
        self.cursor = None
        # get the list of tables
        for model in self.models:
            self.tables.append(model._meta.db_table)

    def __enter__(self):
        self.cursor = connection.cursor()
        # lock the tables
        self.lock(self.cursor, self.tables, self.mode)
        return self.cursor

    def __exit__(self, type, value, traceback):
        # unlock the tables
        self.unlock(self.cursor, self.tables)

    @staticmethod
    def lock(cursor, tables, mode):
        logger.debug('locking the tables {} with {}'.format(', '.join(tables), mode))
        cursor.execute('LOCK TABLE {} IN {} MODE'.format(', '.join(tables), mode))

    @staticmethod
    def unlock(cursor, tables):
        pass


def calc_coop_score(procedures):
    """
    Calculate and return overall COOP prcedure score.

    Args:
        procedures - iterable of either tracker.models.Procedure objects or julia.node.ListValueNode nodes
    """
    score = 0
    if procedures:
        for procedure in procedures:
            try:
                procedure.score
            except AttributeError:
                score += procedure['score'].value
            else:
                score += procedure.score
    return score


def calc_accuracy(weapons, min_ammo=None):
    hits = 0
    shots = 0
    for weapon in weapons:
        if weapon.name in definitions.WEAPONS_FIRED:
            hits += weapon.hits
            shots += weapon.shots
    return int(calc_ratio(hits, shots, min_divisor=min_ammo) * 100)


def calc_ratio(divident, divisor, min_divident=None, min_divisor=None):
    """
    Return quotient result of true division operation for `divident` and `division`

    If either of `min_divident`, `min_divisor` values is greater
    than its corresponding test values, return zero.
    """
    try:
        assert(min_divident is None or divident >= min_divident)
        assert(min_divisor is None or divisor >= min_divisor)
        return divident/divisor
    except (ValueError, TypeError, ZeroDivisionError, AssertionError):
        return 0.0


def force_ipy(ip_address):
    from IPy import IP
    # no conversion is needed
    if isinstance(ip_address, IP):
        return ip_address
    return IP(ip_address)


def force_clean_name(name):
    "Return a name free of SWAT text tags and leading/trailing whitespace."
    while True:
        match = re.search(r'(\[[\\/]?[cub]\]|\[c=[^\[\]]*?\])', name, flags=re.I)
        if not match:
            break
        name = name.replace(match.group(1), '')
    return name.strip()


def force_valid_name(name, ip_address):
    """
    Enforce name for given name, ip address pair.

    If provided name is empty, return the 8 to 16 characters of the sha1 hash 
    derived from the numeric form of the provided IP address. 

    Otherwise return the provided name as is.
    """
    if not name:
        return ('_%s' % 
            hashlib.sha1(force_bytes(force_ipy(ip_address).int())).hexdigest()[8:16]
        )
    return name


def force_name(name, ip_address):
    return force_valid_name(force_clean_name(name), ip_address)


def sort_key(*comparable):
    def key(player):
        stats = []
        for prop in comparable:
            sign = 1
            if prop.startswith('-'):
                sign = -1
                prop = prop[1:]
            stats.append(getattr(player, prop) * sign)
        return stats
    return key


def get_profile_url(profile, view, **kwargs):
    kwargs = kwargs or {}
    kwargs.update({
        'profile_id': profile.pk,
    })
    if profile.name:
        kwargs['slug'] = profile.name
    return reverse(view, kwargs=kwargs)


def rank_dicts(dicts):
    best = {}
    for d in dicts:
        for key, value in six.iteritems(d):
            if key not in best or value > best[key]:
                best[key] = value
    return best