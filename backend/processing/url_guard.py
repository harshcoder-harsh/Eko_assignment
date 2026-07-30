"""SSRF guard for user-supplied import URLs.

Both `/documents/import-url` and `/analytics/import-url` fetch a URL chosen by
the caller and hand the response body back. Without validation that turns the
backend into a proxy into its own network: cloud metadata endpoints
(169.254.169.254), localhost-only admin ports, and RFC1918 addresses all become
reachable by any authenticated tenant user.

`safe_get` resolves the hostname, rejects any address that is not a public
unicast address, and re-validates on every redirect hop (a public host can
302 to 127.0.0.1, so validating only the first URL is not enough).
"""
import ipaddress
import socket
from urllib.parse import urlparse

import requests

ALLOWED_SCHEMES = {"http", "https"}
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 30


class UnsafeUrlError(ValueError):
    """Raised when a URL resolves somewhere we refuse to fetch from."""


def _assert_public_ip(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host '{host}'.") from exc

    if not infos:
        raise UnsafeUrlError(f"Could not resolve host '{host}'.")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        # Covers loopback, RFC1918, link-local (incl. 169.254.169.254 metadata),
        # multicast, reserved, unspecified (0.0.0.0) and IPv6 equivalents.
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(
                "That URL resolves to a private or internal address, which is not allowed."
            )


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError("Only http:// and https:// URLs are supported.")
    if not parsed.hostname:
        raise UnsafeUrlError("That URL has no host.")
    _assert_public_ip(parsed.hostname)
    return url


def safe_get(url: str, *, max_bytes: int, timeout: int = DEFAULT_TIMEOUT,
             user_agent: str = "FlowClaw-RAG/1.0"):
    """Fetch `url` with SSRF validation on every hop and a hard size cap.

    Returns the final `requests.Response` with the body already streamed and
    capped, exposed as `.flowclaw_content`.
    """
    current = url
    headers = {"User-Agent": user_agent}

    for _ in range(MAX_REDIRECTS + 1):
        validate_url(current)
        try:
            resp = requests.get(
                current,
                timeout=timeout,
                stream=True,
                headers=headers,
                allow_redirects=False,  # we follow manually so each hop is checked
            )
        except requests.RequestException as exc:
            raise UnsafeUrlError(f"Could not fetch URL: {exc}") from exc

        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                raise UnsafeUrlError("Redirect without a Location header.")
            current = requests.compat.urljoin(current, location)
            continue

        try:
            resp.raise_for_status()
        except requests.RequestException as exc:
            resp.close()
            raise UnsafeUrlError(f"Could not fetch URL: {exc}") from exc

        content = b""
        for chunk in resp.iter_content(8192):
            content += chunk
            if len(content) > max_bytes:
                resp.close()
                raise UnsafeUrlError(
                    f"File too large (max {max_bytes // (1024 * 1024)} MB)."
                )
        resp.close()
        if not content:
            raise UnsafeUrlError("The URL returned an empty file.")

        resp.flowclaw_content = content
        return resp

    raise UnsafeUrlError("Too many redirects.")