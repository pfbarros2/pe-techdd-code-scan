"""Outbound webhooks: tenants register a URL to receive invoice events."""
import ipaddress
import json
import socket
from urllib.parse import urlparse

import requests

from ..config import settings


def deliver(event: dict, target_url: str) -> int:
    resp = requests.post(
        target_url, data=json.dumps(event), timeout=settings.WEBHOOK_TIMEOUT_SECONDS
    )
    return resp.status_code


def test_webhook(target_url: str) -> str:
    """Called from the settings page so tenants can preview their endpoint."""
    resp = requests.get(target_url, timeout=settings.WEBHOOK_TIMEOUT_SECONDS)
    return resp.text[:2000]


def _is_public_host(hostname: str) -> bool:
    try:
        addr = ipaddress.ip_address(socket.gethostbyname(hostname))
    except (socket.gaierror, ValueError):
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)


def deliver_checked(event: dict, target_url: str) -> int:
    parsed = urlparse(target_url)
    if parsed.scheme != "https" or not parsed.hostname or not _is_public_host(parsed.hostname):
        raise ValueError("webhook target must be a public https URL")
    resp = requests.post(
        target_url,
        data=json.dumps(event),
        timeout=settings.WEBHOOK_TIMEOUT_SECONDS,
        allow_redirects=False,
    )
    return resp.status_code
