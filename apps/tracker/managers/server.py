import json
import logging
import operator as op
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import voluptuous
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from voluptuous import Invalid

from apps.tracker.schema import serverquery_schema
from apps.tracker.aio_tasks.discovery import ServerDiscoveryTask
from apps.tracker.aio_tasks.serverquery import ServerStatusTask, ParsedResponse
from apps.tracker.utils import aio
from apps.utils.misc import dumps

if TYPE_CHECKING:
    from apps.tracker.models import Server  # noqa


logger = logging.getLogger(__name__)


class ServerQuerySet(models.QuerySet):

    def with_status(self, with_empty=False):
        """
        Obtain cached status for all eligible servers in the queryset.

        :return: Ordered list of servers
        :rtype: list
        """
        redis = cache.client.get_client()
        servers = list(self.all())
        redis_keys = [server.address for server in servers]
        result = []

        if redis_keys:
            server_status = redis.hmget(settings.TRACKER_SERVER_REDIS_KEY, redis_keys)
            for i, server in enumerate(servers):
                # cache miss
                if not server_status[i] and not with_empty:
                    continue
                elif not server_status[i]:
                    server.status = None
                else:
                    server.status = json.loads(server_status[i].decode())
                result.append(server)

        return result

    def refresh_status(self) -> tuple[list[tuple['Server', dict[str, Any]]],
                                      list[tuple['Server', Exception] | tuple['Server', Invalid]]]:
        """
        Fetch data for the servers in the queryset, validate response payload then store it in cache.
        Return value is identical to `fetch_info`, except that a query result may also yield a ValidationError

        :return: Return tuple of 1) an ordered list of (server instance, server status) tuples
                                 2) an ordered list if (server instance, exception) tuples
        """
        redis = cache.client.get_client()
        result = self.fetch_status()

        with_status = []
        with_errors = []

        for server, data_or_exc in result.items():
            if isinstance(data_or_exc, Exception):
                logger.debug('failed to retrieve status for %s due to %s: %s', server, type(data_or_exc), data_or_exc)
                with_errors.append((server, data_or_exc))
                continue
            try:
                status = serverquery_schema(data_or_exc)
            except voluptuous.Invalid as exc:
                logger.error('failed to validate %s: %s (%s)', server, exc, data_or_exc, exc_info=True)
                # status is no longer valid, override with the exception
                with_errors.append((server, exc))
                continue
            # ensure we got data for the correct port
            if status['hostport'] != server.port:
                logger.info('join port for server %s:%s does not match reported hostport %s',
                            server.ip, server.port, status['hostport'])
                continue
            with_status.append((server, status))

        logger.info('adding %s servers to redis', len(with_status))
        if with_status:
            redis.hmset(settings.TRACKER_SERVER_REDIS_KEY,
                        {server.address: dumps(query_data).encode()
                         for server, query_data in with_status})

        return with_status, with_errors

    def fetch_status(self) -> dict['Server', OrderedDict | Exception | None]:
        """
        Attempt to fetch info for every server in the queryset.
        Query result may also yield an exception.

        :return: Ordered dict mapping a server instance to its query result
        :rtype: collections.OrderedDict
        """
        tasks = []
        # ensure result is ordered
        result = OrderedDict(
            (server, None) for server in self.all()
        )

        for server in result:
            kwargs = {
                'ip': server.ip,
                'status_port': server.status_port,
            }
            tasks.append(
                ServerStatusTask(
                    callback=lambda server, status: op.setitem(result, server, status),
                    id=server,
                    **kwargs
                )
            )

        logger.debug('%s serverquery tasks in pool', len(tasks))
        aio.run_many(tasks)
        logger.debug('finished %s serverquery tasks', len(tasks))

        return result

    def relist(self):
        return self.update(listed=True, failures=0)

    def enabled(self):
        return self.filter(enabled=True)

    def listed(self):
        return self.enabled().filter(listed=True)


class ServerManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).order_by('-pinned', 'pk')

    def create_server(self, ip, port, **options):
        # attempt to check for duplicates
        if self.filter(ip=ip, port=port).exists():
            raise ValidationError(_('The server has already been registered.'))
        return self.create(ip=ip, port=port, **options)

    def create_servers(self, server_addrs: list[tuple[str, int]]) -> ServerQuerySet:
        """
        Create servers from a list of (server_ip, join_port) tuples.
        Already existing servers are relisted.

        Return queryset for created/existing servers.
        """
        server_pks = set()

        for server_ip, server_port in server_addrs:
            try:
                server, created = self.get_or_create(ip=server_ip, port=server_port)
            except ValidationError as exc:
                logger.info('failed to create server %s:%s due to %s', server_ip, server_port, exc)
                continue
            if created:
                logger.info('created server %s with %s:%s', server.pk, server_ip, server_port)
            # skip disabled servers
            elif not server.enabled:
                logger.info('server %s with %s:%s exists but is disabled', server.pk, server_ip, server_port)
                continue
            server_pks.add(server.pk)

        if not server_pks:
            return self.none()

        return self.filter(pk__in=server_pks)

    def probe_server_addrs(
        self,
        server_addrs: set[tuple[str, int]],
    ) -> dict[tuple[str, int], ParsedResponse | Exception]:
        result = {}
        tasks = []

        for addr in server_addrs:
            server_ip, server_port = addr
            tasks.append(
                ServerStatusTask(callback=lambda addr_port, status: op.setitem(result, addr_port, status),
                                 id=addr,
                                 ip=server_ip,
                                 status_port=server_port + 1)
            )

        aio.run_many(tasks)

        return result

    def discover_server_addrs(self) -> set[tuple[str, int]]:
        """
        Collect server addresses from various sources
        in the form of (ip_addr:join_port) tuples
        """
        result: list[tuple[str, list[tuple[str, str]]]] = []
        tasks: list[ServerDiscoveryTask] = []

        for item in settings.TRACKER_SERVER_DISCOVERY:
            url = item['url']
            parser_import_path = item['parser']

            try:
                parser = import_string(parser_import_path)
            except ImportError as exc:
                logger.error('failed to import parser %s: %s', parser_import_path, exc, exc_info=True)
                continue

            tasks.append(
                ServerDiscoveryTask(
                    callback=lambda _url, res: result.append((_url, res)),
                    id=url,
                    url=url,
                    parser=parser,
                )
            )

        logger.debug('%s server discovery tasks in pool', len(tasks))
        aio.run_many(tasks)
        logger.debug('finished %s server discovery tasks', len(tasks))

        # remove duplicate ips
        server_addrs = set()
        for url, discovery_result in result:
            if isinstance(discovery_result, Exception):
                logger.warning('got exception while scraping %s: %s(%s)',
                               url, type(discovery_result).__name__, discovery_result)
            elif not discovery_result:
                logger.info('received no servers from %s', url)
            else:
                logger.info('received %s servers from %s', len(discovery_result), url)
                server_addrs |= set(discovery_result)

        if not server_addrs:
            logger.warning('discovered no servers from %s sources',
                           len(settings.TRACKER_SERVER_DISCOVERY),
                           extra={'data': {'result': result}})

        return {
            (server_ip, int(server_port))
            for server_ip, server_port in server_addrs
        }

    def discover_servers(self) -> ServerQuerySet:
        discovered_server_addrs = self.discover_server_addrs()
        probed_servers = self.probe_server_addrs(discovered_server_addrs)

        checked_server_addrs = []
        for (server_ip, server_port), resp_or_exc in probed_servers.items():
            if isinstance(resp_or_exc, Exception):
                continue
            try:
                status = serverquery_schema(resp_or_exc)
            except voluptuous.Invalid as exc:
                logger.exception('failed to validate data from %s:%s: %s due to %s',
                                 server_ip, server_port, resp_or_exc, exc)
                continue

            if status['hostport'] != server_port:
                logger.info('join port for server %s:%s does not match reported hostport %s',
                            server_ip, server_port, status['hostport'])
                continue

            checked_server_addrs.append((server_ip, server_port))

        if not checked_server_addrs:
            logger.info('discovered no live servers')
            return self.none()

        logger.info('discovered %s online servers', len(checked_server_addrs))
        servers = self.create_servers(checked_server_addrs)
        servers.relist()

        return servers

    def discover_query_ports(self) -> None:
        """
        Scan extra query ports for all listed servers.
        If an extra port yields GS1 or AMMod response then change the server's status port to the discovered one.
        """
        probe_results = self._probe_extra_query_ports(self.listed())
        # collect server addresses that succeeded the probe
        probed_query_ports: dict[tuple[str, int], list[dict[str, int | bool]]] = {}
        for (server_ip, server_port, query_port), data_or_exc in probe_results.items():
            if isinstance(data_or_exc, Exception):
                continue
            try:
                status = serverquery_schema(data_or_exc)
            except voluptuous.Invalid as exc:
                logger.info('failed to validate data from %s:%s: %s due to %s',
                            server_ip, server_port, data_or_exc, exc)
                continue

            if status['hostport'] != server_port:
                logger.info('join port for server %s:%s does not match reported hostport %s',
                            server_ip, server_port, status['hostport'])
                continue

            probed_query_ports.setdefault((server_ip, server_port), []).append({
                'port': query_port,
                'is_gs1': status['swatwon'] is not None,
                'is_am': status['numrounds'] is not None,
            })

        if not probed_query_ports:
            return

        for (server_ip, server_port), query_ports in probed_query_ports.items():
            # we are interested in either GS1 or AdminMod's ServerQuery ports
            query_ports = sorted(query_ports, key=lambda item: (item['is_gs1'], item['is_am']), reverse=True)
            preferred_status_port = query_ports[0]['port']

            logger.debug('discovered %d ports for %s:%s: %s',
                         len(query_ports), server_ip, server_port,
                         ', '.join(f'{item["port"]} [GS1={item["is_gs1"]}, AM={item["is_am"]}]'
                                   for item in query_ports))

            update_qs = self.filter(Q(ip=server_ip, port=server_port) & ~Q(status_port=preferred_status_port))
            if update_qs.update(status_port=preferred_status_port):
                logger.info('updated status port for server %s:%s to %s',
                            server_ip, server_port, preferred_status_port)

    def _probe_extra_query_ports(self, qs: ServerQuerySet) -> dict[tuple[str, int, int], ParsedResponse | Exception]:
        results = {}
        tasks: list[ServerStatusTask] = []

        for server in qs:
            # probe the ports in the range of join port +1 - +4
            for query_port in range(server.port + 1, server.port + 5):
                server_tri_addr = (server.ip, server.port, query_port)
                tasks.append(
                    ServerStatusTask(
                        callback=lambda addr, status: op.setitem(results, addr, status),
                        id=server_tri_addr,
                        ip=server.ip,
                        status_port=query_port
                    )
                )

        aio.run_many(tasks)

        return results
