from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class UrlSafetyResult:
    is_safe: bool
    normalized_url: str | None
    display_url: str | None
    errors: list[str]


class SafeUrlValidator:
    def __init__(self, *, allow_private_destinations: bool) -> None:
        self.allow_private_destinations = allow_private_destinations

    def validate_source_url(self, raw_url: str, *, resolve_dns: bool = True) -> UrlSafetyResult:
        return self._validate(raw_url, resolve_dns=resolve_dns, enforce_public_network=True)

    def validate_stream_url(self, raw_url: str) -> UrlSafetyResult:
        return self._validate(raw_url, resolve_dns=False, enforce_public_network=False)

    def _validate(
        self,
        raw_url: str,
        *,
        resolve_dns: bool,
        enforce_public_network: bool,
    ) -> UrlSafetyResult:
        errors: list[str] = []
        stripped_url = raw_url.strip()
        if not stripped_url:
            return UrlSafetyResult(False, None, None, ["URL is required."])

        if any(ord(character) < 32 for character in stripped_url):
            return UrlSafetyResult(False, None, None, ["URL contains invalid control characters."])

        parsed = urlparse(stripped_url)
        if parsed.scheme not in {"http", "https"}:
            return UrlSafetyResult(False, None, None, ["Only HTTP and HTTPS playlist URLs are supported."])
        if not parsed.hostname:
            return UrlSafetyResult(False, None, None, ["URL must include a host name."])
        try:
            parsed.port
        except ValueError:
            return UrlSafetyResult(False, None, None, ["URL includes an invalid port."])
        if "\\" in parsed.path:
            return UrlSafetyResult(False, None, None, ["URL path contains invalid backslashes."])

        host = parsed.hostname
        if enforce_public_network and not self.allow_private_destinations:
            errors.extend(self._private_destination_errors(host, resolve_dns=resolve_dns))

        display_url = self.redact_url(stripped_url)
        return UrlSafetyResult(not errors, stripped_url if not errors else None, display_url, errors)

    def _private_destination_errors(self, host: str, *, resolve_dns: bool) -> list[str]:
        host_lower = host.lower().rstrip(".")
        if host_lower in {"localhost", "localhost.localdomain"}:
            return ["Localhost source URLs are blocked by the default private-network policy."]

        addresses: set[str] = set()
        try:
            addresses.add(str(ipaddress.ip_address(host_lower.strip("[]"))))
        except ValueError:
            if resolve_dns:
                try:
                    for result in socket.getaddrinfo(host_lower, None):
                        sockaddr = result[4]
                        addresses.add(str(sockaddr[0]))
                except socket.gaierror:
                    return ["Host name could not be resolved."]

        for address in addresses:
            ip_address = ipaddress.ip_address(address)
            if (
                ip_address.is_private
                or ip_address.is_loopback
                or ip_address.is_link_local
                or ip_address.is_multicast
                or ip_address.is_reserved
                or ip_address.is_unspecified
            ):
                return [
                    "URL resolves to a private, local, or reserved network address. "
                    "Enable private source URLs only for trusted home-lab sources."
                ]
        return []

    @staticmethod
    def redact_url(raw_url: str) -> str:
        parsed = urlparse(raw_url)
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path or ""
        query = "?..." if parsed.query else ""
        return f"{parsed.scheme}://{host}{port}{path}{query}"
