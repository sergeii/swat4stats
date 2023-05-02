from dataclasses import dataclass
from ipaddress import IPv4Network


@dataclass
class WhoisQueryResult:
    description: str | None
    country: str | None
    cidr: IPv4Network
