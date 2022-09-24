import asyncio
import socket
import re
import logging
from typing import Any

from django.conf import settings

from apps.tracker.utils import aio


logger = logging.getLogger(__name__)

ParsedResponse = dict[str, str | list[dict[str, str]]]


class ServerStatusTask(aio.Task):
    """Async task for making GameSpy1 status requests."""

    class ResponseMalformed(Exception):
        pass

    class ResponseIncomplete(Exception):
        pass

    status_buf_size = 2048
    status_query = b'\\status\\'
    semaphore = asyncio.Semaphore(settings.TRACKER_STATUS_CONCURRENCY)

    def __init__(self, *, ip: str, status_port: int, **kwargs: Any) -> None:
        self.ip = ip
        self.status_port = status_port
        self.status_addr = (self.ip, self.status_port)
        super().__init__(**kwargs)

    @aio.with_semaphore(semaphore)
    @aio.with_timeout(settings.TRACKER_STATUS_TIMEOUT)
    async def start(self) -> ParsedResponse:
        loop = asyncio.get_running_loop()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        packets = []

        try:
            logger.debug('connecting %s', sock)
            await loop.sock_connect(sock, self.status_addr)
            logger.debug('sending query to %s', sock)
            await loop.sock_sendall(sock, self.status_query)
            # read as many packets as possible to rebuild the original payload
            while True:
                logger.debug('reading %s from %s', self.status_buf_size, sock)
                buf = await loop.sock_recv(sock, self.status_buf_size)
                logger.debug('received %s from %s', buf, sock)
                packets.append(buf)
                try:
                    payload = self._collect_status_payload(packets)
                except self.ResponseIncomplete:
                    continue
                else:
                    return self._expand_status_payload(payload)
        except Exception as e:
            logger.debug('closing socket %s %s', sock, type(e))
            sock.shutdown(socket.SHUT_RDWR)
            raise

    def _parse_status_payload(self, data: str) -> list[tuple[str, str]]:
        """
        Split a response payload into a list of key, value pairs.

        :param data: Response payload
        :return: List of (key, value) pairs
        """
        params = []
        split = data.split('\\')
        for i, key in enumerate(split):
            # skip values
            if not i % 2:
                continue
            try:
                value = split[i + 1]
            except IndexError:
                pass
            else:
                params.append((key, value))
        return params

    def _expand_status_payload(self, data: str) -> ParsedResponse:
        """
        Expand a status payload into a dictionary mapping status keys to its values.
        Player and COOP objective params are additionally expanded into lists.

        """
        result = {
            'players': {},
            'objectives': [],
        }

        for param, value in self._parse_status_payload(data):
            # e.g. \obj_Neutralize_All_Enemies\0\
            # -> {objectives: [{name: Neutralize_All_Enemies, status': 0}, ...]}
            obj_match = re.match(r'^obj_(?P<name>.+)$', param)
            # parse objectives into a list of objective objects
            if obj_match:
                result['objectives'].append({
                    'name': obj_match.group('name'),
                    'status': value,
                })
                continue
            # \player_2\James_Bond_007\
            # -> {players: {2: {id: 2, player: James_Bond_007}}}
            player_match = re.match(r'(?P<param>.+)_(?P<id>\d+)$', param)
            # collect player params into a dict mapping player id to params
            if player_match:
                player_id, player_param = player_match.group('id'), player_match.group('param')
                player = result['players'].setdefault(player_id, {'id': player_id})
                player[player_param] = value
                continue
            # map every other param
            result[param] = value

        # players has to be a sorted list
        # {players: [{id: 2, player: James_Bond_007,...}},...]
        result['players'] = sorted(result['players'].values(),
                                   key=lambda player: int(player['id']))

        return result

    def _collect_status_payload(self, packets: list[bytes]) -> str:
        """
        Attempt to sort response packets and normalize response payload.

        :param packets: List of received packets (possibly unordered)
        :return: Normalized response payload

        :raises ResponseIncomplete: if not enough packets received
        :raises ResponseMalformed: if one of the packets contains corrupt data
        """
        count = None
        ordered = {}

        for packet in map(self._decode_response, packets):
            order = None
            is_final = False
            params = self._parse_status_payload(packet)
            for param, value in params:
                # ^\statusresponse\1 or \queryid\1$
                if order is None and param in ('statusresponse', 'queryid'):
                    try:
                        order = int(value)
                    # \queryid\1.1$
                    except ValueError:
                        order = 1
                    else:
                        # statusresponse is zero based
                        order += (param == 'statusresponse')
                # this is the final packet so we should expect as many packets
                # as the number of the final packet
                elif param == 'final':
                    is_final = True

            if is_final:
                count = order

            if order is None:
                raise self.ResponseMalformed('no order specified')

            ordered[order] = packet

        if not count or count != len(ordered):
            raise self.ResponseIncomplete(f'received {len(ordered)} of {count}')

        # sort packets by their order
        packets = (self._normalize_status_packet(value) for _, value in sorted(ordered.items()))
        payload = ''.join(packets)

        return payload

    def _normalize_status_packet(self, data: str) -> str:
        """
        Attempt to remove "statusresponse" and "eof" params from packet contents

        :param data: Packet contents
        :return: Normalized packet contents
        """
        return re.sub(r'^\\statusresponse\\\d+(.+)\\eof\\$', r'\1', data)

    def _decode_response(self, data: bytes) -> str:
        return data.decode(encoding='latin-1')
