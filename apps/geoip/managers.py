import datetime
import logging
from ipaddress import IPv4Address, IPv4Network
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Case, When, F, Q, Value, QuerySet
from django.utils import timezone
from ipwhois import IPWhois
from ipwhois.utils import ipv4_is_defined

from apps.geoip.entities import WhoisQueryResult

if TYPE_CHECKING:
    from apps.geoip.models import ISP  # noqa

logger = logging.getLogger(__name__)


class IPManager(models.Manager):

    def get_queryset(self) -> QuerySet:
        """
        Return a queryset with an extra `length` field that
        is equal to the number of ip addresses in the ip range.
        """
        min_freshness_date = timezone.now() - datetime.timedelta(seconds=settings.GEOIP_IP_EXPIRY)
        return (super().get_queryset()
                .annotate(length=Case(When(Q(range_to__gt=1), then=F('range_to') - F('range_from')),
                                      default=0,
                                      output_field=models.IntegerField()),
                          is_fresh=Case(When(Q(date_created__gte=min_freshness_date), then=Value(True)),
                                        default=Value(False),
                                        output_field=models.BooleanField())))

    def expired(self) -> QuerySet:
        """Return old IP entries pending removal"""
        return self.get_queryset().filter(is_fresh=False)


class ISPManager(models.Manager):

    def match(self, ip_address: str | IPv4Address) -> tuple['ISP', int]:
        """
        Attempt to find an ISP entry matching the provided IP address.

        Return a tuple containing the matched isp object
        alongside with the number of addresses in the matched ip range.
        """
        from apps.geoip.models import IP

        ip_address = IPv4Address(ip_address)
        ip_int = int(ip_address)
        obj = (IP.objects
               .select_related('isp')
               .filter(range_from__lte=ip_int, range_to__gte=ip_int)
               .extra(order_by=('length',))[:1]
               .get())
        return obj.isp, obj.length

    def match_or_create(self, ip_address: str | IPv4Address) -> tuple['ISP', bool]:
        from apps.geoip.models import IP

        ip_address = IPv4Address(ip_address)
        fallback_obj = None
        # match against the known networks
        try:
            matched_obj, length = self.match(ip_address)
        except ObjectDoesNotExist:
            pass
        else:
            # do an extra lookup if the addr num besides the acceptable limit
            if length > settings.GEOIP_ACCEPTED_IP_LENGTH:
                logger.info('existing IP range for %s is too broad: %s', ip_address, length)
                # but keep it for fallback
                fallback_obj = matched_obj
            else:
                return matched_obj, False

        # if unable to obtain acceptable IP range for this address, then do a whois lookup
        try:
            network_data = self._query_ip_address(ip_address)
        except Exception as exc:
            logger.warning('unable to query whois for %s due to %s(%s)',
                           ip_address, type(exc).__name__, exc, exc_info=True)
            return fallback_obj, False

        loopkup_items = {}
        # ISP/Organization name
        if network_data.description:
            loopkup_items['name'] = network_data.description
        # Usually this is the organization's contry
        if network_data.country:
            loopkup_items['country'] = network_data.country

        with transaction.atomic():
            # attempt to insert the ip range details
            ip_obj, created = (IP.objects
                               .select_related('isp')
                               .get_or_create(range_from=int(network_data.cidr[0]),
                                              range_to=int(network_data.cidr[-1])))
            # we performed an extra lookup but the same ip range was resolved
            if not created:
                logger.info('IP range %s-%s already belongs to %s',
                            network_data.cidr[0], network_data.cidr[-1], ip_obj.isp)
                return ip_obj.isp, created
            # if isp name is empty, return a new entry without further lookup
            if 'name' not in loopkup_items:
                isp = self.get_queryset().create(**loopkup_items)
                created = True
                # otherwise perform a lookup (still with a possibility of creating a brand-new object)
            else:
                isp, created = (self.get_queryset()
                                .filter(name__isnull=False,
                                        country__isnull=('country' not in loopkup_items))  # country may be null
                                .get_or_create(**loopkup_items))
            # append the created ip range entry
            isp.ip_set.add(ip_obj)
            return isp, created

    def _query_ip_address(self, ip_address: IPv4Address) -> WhoisQueryResult:
        """
        Query given ip address against with whois.
        Return a dictionary of network name, country and its cidr.
        """

        # loopback address, private range, etc
        is_defined, defined_network_name, _ = ipv4_is_defined(ip_address)
        if is_defined:
            return WhoisQueryResult(description=defined_network_name, country=None, cidr=IPv4Network(ip_address))

        try:
            whois_data = IPWhois(str(ip_address)).lookup_whois()
            logger.info('received whois for %s: %s', ip_address, whois_data)
        except Exception as exc:
            logger.info('failed to query whois for %s due to %s(%s)', ip_address, type(exc).__name__, exc)
            raise

        if not whois_data.get('nets'):
            raise ValueError('whois data contains no nets')

        network_data = whois_data['nets'][0]
        # multiple cidrs may coexist, seperated with commas
        if ',' in network_data['cidr']:
            cidr = self._pick_proper_cidr_from_list(ip_address, network_data['cidr'])
        else:
            cidr = IPv4Network(network_data['cidr'])

        # range end address must be always greater than the range start address
        if not cidr[0] <= cidr[-1]:
            raise ValueError('Invalid IP range')
        # the ip must fit into the resolved range
        if not cidr[0] <= ip_address <= cidr[-1]:
            raise ValueError('Unexpected IP range')

        if net_description := network_data.get('description'):
            description = self._format_network_description(net_description)
        else:
            description = None

        if net_country := network_data.get('country'):
            country = net_country.lower()
        else:
            country = None

        return WhoisQueryResult(description=description, country=country, cidr=cidr)

    def _format_network_description(self, raw_description: str) -> str | None:
        if not (description := raw_description.strip()):
            return None
        return description.splitlines()[0][:255]

    def _pick_proper_cidr_from_list(self, ip_address: IPv4Address, cidr: str) -> IPv4Network:
        ip_address_obj = IPv4Address(ip_address)
        for cidr_v4 in cidr.split(','):
            cidr_v4 = cidr_v4.strip()
            if cidr_v4:
                cidr_obj = IPv4Network(cidr_v4)
                if ip_address_obj in cidr_obj:
                    return cidr_obj
        raise ValueError('cidr list does not contain required range')
