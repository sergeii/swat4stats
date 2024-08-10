import csv
import io
import json
import re

re_ipv4 = (
    r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
)
re_port = r"\d{1,5}"


def plain_ip_port(content: bytes) -> list[tuple[str, str]]:
    re_pattern = re.compile(rf"\b(?P<addr>{re_ipv4}):(?P<port>{re_port})\b", flags=re.MULTILINE)
    html = content.decode(errors="ignore")
    return re_pattern.findall(html)


def html_ip_port(content: bytes) -> list[tuple[str, str]]:
    re_pattern = re.compile(
        rf"\b(?P<addr>{re_ipv4})[^:]*:[^\d]*(?P<port>{re_port})\b",
        flags=re.MULTILINE,
    )
    html = content.decode(errors="ignore")
    return re_pattern.findall(html)


def csv_two_columns(content: bytes) -> list[tuple[str, str]]:
    addresses = []
    csv_reader = csv.reader(io.StringIO(content.decode("utf-8")))
    for row in csv_reader:
        if len(row) < 2:  # noqa: PLR2004
            continue
        addresses.append((row[0], row[1]))
    return addresses


def master_server_api(content: bytes) -> list[tuple[str, str]]:
    servers = json.loads(content)
    return [(server["ip"], server["port"]) for server in servers]
