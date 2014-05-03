# -*- coding: utf-8 -*-
from __future__ import (unicode_literals, absolute_import)

import logging
from optparse import make_option

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Min
from cacheops.invalidation import invalidate_all
from whois import int2ip

import stats7
import tracker

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--insert',
            action='store_true',
            dest='insert',
            default=False,
        ),
    )

    def handle(self, *args, **options):
        invalidate_all()
        ips_total = 0
        ips_checked = []
        self.stdout.write('about to check %d IP addresses' % stats7.models.RoundPlayer.objects.count())
        for rp in stats7.models.RoundPlayer.objects.all():
            ips_total += 1
            ip = int2ip(rp.ip)

            if ip in ips_checked:
                continue
            ips_checked.append(ip)
            
            #logger.debug('checking %s' % ip)
            if not options['insert']:
                try:
                    isp = tracker.models.ISP.objects.match(ip)
                except ObjectDoesNotExist:
                    logger.warning('failed to match %s' % ip)
            else:
                isp, created = tracker.models.ISP.objects.match_or_create(ip)
                if created:
                    logger.debug('retrieved info for %s %s, %s' % (ip, isp.name, isp.country))
            if not ips_total % 1000:
                self.stdout.write('%d IPs checked' % ips_total)
