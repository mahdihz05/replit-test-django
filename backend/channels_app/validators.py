import re
import socket
import ipaddress
import requests
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional, List
from requests.adapters import HTTPAdapter


WORDPRESS_REQUEST_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 Chrome/138 Safari/537.36 Mohtavayar-WordPress/1.0'
)


def _is_private_ip(ip: str) -> bool:
    try:
        parsed = ipaddress.ip_address(ip)
        return (
            parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_multicast
            or parsed.is_reserved
            or parsed.is_unspecified
        )
    except ValueError:
        # Fail closed: if we can't parse it, treat it as unsafe.
        return True


def _resolve_all_ips(hostname: str) -> List[str]:
    """Return all public IPv4 and IPv6 addresses for a hostname."""
    ips = set()
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            for info in socket.getaddrinfo(hostname, None, family):
                ip = info[4][0]
                ips.add(ip)
        except (socket.gaierror, OSError):
            continue
    return list(ips)


class PinnedHostAdapter(HTTPAdapter):
    """
    Connect to a specific IP while preserving the original hostname for
    the HTTP Host header, TLS SNI, and certificate verification.
    """

    def __init__(self, hostname: str, ip: str, *args, **kwargs):
        self._hostname = hostname
        self._ip = ip
        super().__init__(*args, **kwargs)

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        host_params, ssl_params = super().build_connection_pool_key_attributes(request, verify, cert)
        # requests 2.32+/urllib3 2.x pass these values directly to
        # connection_from_host(host=..., port=..., scheme=...).  Using the
        # older/internal ``hostname`` key raises an unexpected keyword error.
        host_params['host'] = self._ip
        ssl_params['server_hostname'] = self._hostname
        ssl_params['assert_hostname'] = self._hostname
        return host_params, ssl_params


def is_safe_url(url: str) -> bool:
    """
    SSRF guard: reject URLs that use non-HTTP schemes, point to localhost by name,
    or resolve to any private/loopback/link-local/reserved/multicast IP address.
    """
    if not url:
        return False

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Reject literal special hostnames by default.
    lower = hostname.lower()
    if lower in ('localhost', '127.0.0.1', '::1'):
        from django.conf import settings
        return bool(getattr(settings, 'DEBUG', False))

    # Reject common internal-only TLDs / hostnames.
    if lower.endswith(('.local', '.internal', '.lan', '.corp', '.home')):
        from django.conf import settings
        return bool(getattr(settings, 'DEBUG', False))

    # Resolve DNS and reject if any resolved IP is non-public.
    ips = _resolve_all_ips(hostname)
    if not ips:
        return False
    return all(not _is_private_ip(ip) for ip in ips)


def normalize_site_url(url: str) -> str:
    url = url.strip().rstrip('/')
    if not url.startswith('http://') and not url.startswith('https://'):
        url = f'https://{url}'
    return url


def _safe_session(url: str):
    """Return a requests Session pinned to the first resolved public IP of the URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    netloc = parsed.netloc
    ips = _resolve_all_ips(hostname)
    if not ips or any(_is_private_ip(ip) for ip in ips):
        raise requests.RequestException('URL resolves to non-public IP')

    ip = ips[0]
    session = requests.Session()
    # Environment proxies would receive the pinned destination instead of the
    # adapter opening the verified direct connection. Keep this SSRF-sensitive
    # path deterministic and independent from HTTP(S)_PROXY.
    session.trust_env = False
    adapter = PinnedHostAdapter(hostname, ip)
    # Mount on the full netloc (host:port) so explicit ports are matched.
    prefix = f'{parsed.scheme}://{netloc}/'
    session.mount(prefix, adapter)
    return session, ip, hostname


def safe_request(method: str, url: str, max_redirects: int = 5, **kwargs):
    """
    Make an HTTP request with the connection pinned to a validated public IP,
    manual redirect following, and SSRF validation at every hop.
    """
    if not is_safe_url(url):
        raise requests.RequestException('URL is not safe')

    current_url = url
    session, _, hostname = _safe_session(current_url)
    headers = dict(kwargs.pop('headers', {}) or {})
    # Some WordPress hosting firewalls reject requests' default python-requests
    # user agent even when the REST API is public. Use a browser-compatible
    # agent while retaining an integration identifier for server logs.
    headers.setdefault('User-Agent', WORDPRESS_REQUEST_USER_AGENT)
    headers['Host'] = hostname
    response = session.request(method, current_url, headers=headers, allow_redirects=False, **kwargs)

    for _ in range(max_redirects):
        if response.status_code not in (301, 302, 303, 307, 308):
            break
        location = response.headers.get('Location')
        if not location:
            break
        # Resolve relative redirects against the current response URL.
        current_url = urljoin(response.url, location)
        if not is_safe_url(current_url):
            raise requests.RequestException('Redirect target is not safe')
        next_session, _, next_hostname = _safe_session(current_url)
        next_headers = dict(headers)
        next_headers['Host'] = next_hostname
        response = next_session.request(method, current_url, headers=next_headers, allow_redirects=False, **kwargs)
    return response


def safe_get(url: str, **kwargs):
    return safe_request('GET', url, **kwargs)


def safe_post(url: str, **kwargs):
    return safe_request('POST', url, **kwargs)
