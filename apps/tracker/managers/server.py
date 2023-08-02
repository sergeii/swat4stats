import json
import logging
import operator as op
import random
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import voluptuous
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from voluptuous import Invalid

from apps.tracker.exceptions import MergeServersError
from apps.tracker.schema import serverquery_schema
from apps.tracker.aio_tasks.discovery import ServerDiscoveryTask
from apps.tracker.aio_tasks.serverquery import ServerStatusTask, ServerInfo
from apps.tracker.utils import aio
from apps.utils.misc import dumps, concat_it

if TYPE_CHECKING:
    from apps.tracker.models import Server  # noqa


logger = logging.getLogger(__name__)


class ServerQuerySet(models.QuerySet):

    def with_status(self, *, with_empty: bool = False) -> list['Server']:
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
            server_status = redis.hmget(settings.TRACKER_STATUS_REDIS_KEY, redis_keys)
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
                logger.exception('failed to validate %s: %s (%s)', server, exc, data_or_exc)
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
            redis.hmset(settings.TRACKER_STATUS_REDIS_KEY,
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
            tasks.append(
                ServerStatusTask(
                    callback=lambda server, status: op.setitem(result, server, status),
                    result_id=server,
                    ip=server.ip,
                    status_port=server.status_port,
                )
            )

        aio.run_many(tasks, concurrency=settings.TRACKER_STATUS_QUERY_CONCURRENCY)

        return result

    def relist(self):
        return self.filter(listed=False).update(listed=True, failures=0)

    def reset_failures(self):
        return self.filter(failures__gt=0).update(failures=0)

    def enabled(self):
        return self.filter(enabled=True)

    def listed(self):
        return self.enabled().filter(listed=True)


class ServerManager(models.Manager):

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).order_by('pk')

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

    def merge_servers(self, *, main: 'Server', merged: list['Server'], no_savepoint: bool = False) -> None:
        main_id = main.pk
        merged_ids = [server.pk for server in merged]

        # cannot merge to a server that is already merged
        if main.merged_into is not None:
            raise MergeServersError('cannot merge to a merged server')

        # need at least one server to merge
        if not merged_ids:
            raise MergeServersError('too few servers to merge')

        # cannot merge a server into itself
        if main_id in merged_ids:
            raise MergeServersError('cannot merge a server into itself')

        with transaction.atomic(savepoint=not no_savepoint):
            self._merge_servers(main_id, merged_ids)

    def _merge_servers(self, main_id: int, merged_ids: list[int]) -> None:
        from apps.tracker.models import Game

        merged_ids_str = concat_it(merged_ids)

        logger.info('updating games of servers %s to %s', merged_ids_str, main_id)
        affected_games_cnt = (Game.objects
                              .filter(~Q(server_id=main_id), server_id__in=merged_ids)
                              .update(server_id=main_id))
        logger.info('finished updating %s games of servers %s to %s', affected_games_cnt, merged_ids_str, main_id)

        # disable merged servers and save merge reference to the main server
        affected_servers_cnt = (
            self
            .filter(~Q(pk=main_id), merged_into__isnull=True, pk__in=merged_ids)
            .update(enabled=False, merged_into=main_id, merged_into_at=timezone.now())
        )
        if affected_servers_cnt != len(merged_ids):
            raise MergeServersError('failed to merge all servers')

        # also update references for those servers
        # that were earlier merged into the servers that are being merged right now
        indirect_servers_qs = (self
                               .filter(~Q(pk=main_id), Q(merged_into__in=merged_ids))
                               .values_list('pk', flat=True))
        if indirect_servers_ids := list(indirect_servers_qs):
            # don't update merged_into_at because the server were already merged
            self.filter(pk__in=indirect_servers_ids).update(merged_into=main_id)
            logger.info('updated merge references for %d servers %s to %s',
                        len(indirect_servers_ids), concat_it(indirect_servers_ids), main_id)

    def probe_server_addr(self, server_addr: tuple[str, int]) -> ServerInfo | Exception:
        """Probe a server address for its status"""
        server_ip, server_port = server_addr
        result = []

        task = ServerStatusTask(
            callback=lambda _, status: result.append(status),
            ip=server_ip,
            status_port=server_port + 1,
        )
        aio.run_many([task])

        return result[0]

    def discover_published_servers(self) -> ServerQuerySet:
        published_addrs = self._discover_published_addrs()
        probed_servers = self._probe_published_addrs(published_addrs)

        good_server_addrs = []
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

            good_server_addrs.append((server_ip, server_port))

        if not good_server_addrs:
            logger.info('discovered no live servers')
            return self.none()

        servers = self.create_servers(good_server_addrs)
        relisted = servers.relist()
        logger.info('discovered %d good servers; accepted %d; relisted %d',
                    len(good_server_addrs), len(servers), relisted)

        return servers

    def _discover_published_addrs(self) -> set[tuple[str, int]]:
        """
        Collect server addresses from various sources
        in the form of (ip_addr:join_port) tuples
        """
        result: list[tuple[str, list[tuple[str, str]]]] = []
        tasks: list[ServerDiscoveryTask] = []

        for source in settings.TRACKER_SERVER_DISCOVERY_SOURCES:
            url = source['url']
            parser_import_path = source['parser']

            try:
                parser = import_string(parser_import_path)
            except ImportError as exc:
                logger.exception('failed to import parser %s: %s', parser_import_path, exc)
                continue

            tasks.append(
                ServerDiscoveryTask(
                    callback=lambda source_url, res: result.append((source_url, res)),
                    result_id=url,
                    url=url,
                    parser=parser,
                )
            )

        aio.run_many(tasks)

        # remove duplicate ips
        server_addrs: set[tuple[str, str]] = set()
        for url, maybe_parsed_addrs in result:
            if isinstance(maybe_parsed_addrs, Exception):
                logger.warning('got exception while scraping %s: %s(%s)',
                               url, type(maybe_parsed_addrs).__name__, maybe_parsed_addrs)
            elif not maybe_parsed_addrs:
                logger.info('received no servers from %s', url)
            else:
                logger.info('received %s servers from %s', len(maybe_parsed_addrs), url)
                server_addrs |= set(maybe_parsed_addrs)

        if not server_addrs:
            logger.warning('discovered no servers from %s sources',
                           len(settings.TRACKER_SERVER_DISCOVERY_SOURCES))

        return {
            (server_ip, int(server_port))
            for server_ip, server_port in server_addrs
        }

    def _probe_published_addrs(
        self,
        addrs: set[tuple[str, int]],
    ) -> dict[tuple[str, int], ServerInfo | Exception]:
        result = {}
        tasks = []

        for addr in addrs:
            server_ip, server_port = addr
            tasks.append(
                ServerStatusTask(callback=lambda addr_port, status: op.setitem(result, addr_port, status),
                                 result_id=addr,
                                 ip=server_ip,
                                 status_port=server_port + 1)
            )

        aio.run_many(tasks, concurrency=settings.TRACKER_SERVER_DISCOVERY_PROBE_CONCURRENCY)

        return result

    def discover_good_query_ports(self) -> None:
        """
        Scan extra query ports for all listed servers.
        If an extra port yields GS1 or AMMod response then change the server's status port to the discovered one.
        """
        probe_results = self._probe_good_query_ports(self.listed())
        probed_query_ports: dict[tuple[str, int], list[dict[str, int | bool]]] = {}
        # collect server addresses that succeeded the probe
        for (server_ip, server_port, query_port), data_or_exc in probe_results.items():
            if isinstance(data_or_exc, Exception):
                logger.debug('failed to probe %s:%s (%s) due to %s(%s)',
                             server_ip, server_port, query_port, type(data_or_exc).__name__, data_or_exc)
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
                         concat_it(f'{item["port"]} [GS1={item["is_gs1"]}, AM={item["is_am"]}]'
                                   for item in query_ports))

            update_qs = self.filter(Q(ip=server_ip, port=server_port) & ~Q(status_port=preferred_status_port))
            if update_qs.update(status_port=preferred_status_port):
                logger.info('updated status port for server %s:%s to %s',
                            server_ip, server_port, preferred_status_port)

    def _probe_good_query_ports(self, qs: ServerQuerySet) -> dict[tuple[str, int, int], ServerInfo | Exception]:
        results = {}
        tasks: list[ServerStatusTask] = []

        for server in qs:
            # probe the ports in the range of join port +1 - +4
            for query_port in range(server.port + 1, server.port + 5):
                server_tri_addr = (server.ip, server.port, query_port)
                tasks.append(
                    ServerStatusTask(
                        callback=lambda addr, status: op.setitem(results, addr, status),
                        result_id=server_tri_addr,
                        ip=server.ip,
                        status_port=query_port
                    )
                )

        # shuffle the tasks to avoid probing multiple ports of the same server at a time
        random.shuffle(tasks)

        aio.run_many(tasks, concurrency=settings.TRACKER_PORT_DISCOVERY_CONCURRENCY)

        return results
