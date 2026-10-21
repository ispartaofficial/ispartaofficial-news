"""Bounded, anonymous public reads. Adapted from the established source fetcher.

No authentication, missing-robots exception or TLS override. Explicitly reviewed
hosts may use one timeout retry per run, never an HTTP/robots/TLS bypass.
Each redirect is checked against both the host allowlist and that host's robots.
"""
from __future__ import annotations

import codecs
import ipaddress
import re
import socket
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

AGENT = 'IspartaOfficial/0.1 (+https://github.com/ispartaofficial/ispartaofficial-news)'
MAX_BYTES = 2_000_000


class FetchError(ValueError):
    """Controlled code suitable for the public health report."""


def safe_url(url, hosts):
    try:
        p = urlsplit(url)
        if (p.scheme != 'https' or p.hostname not in hosts or p.username
                or p.password or p.port not in (None, 443)):
            raise FetchError('url_not_approved')
        addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
    except (OSError, ValueError) as exc:
        if isinstance(exc, FetchError):
            raise
        raise FetchError('dns_or_url_invalid') from None
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise FetchError('non_public_destination')
    return p._replace(fragment='').geturl()


def decode(body, content_type):
    header = re.search(r'charset\s*=\s*["\']?([\w.-]+)', content_type, re.I)
    prefix = body[:4096].decode('ascii', errors='ignore')
    document = re.search(r'<meta\b[^>]*charset\s*=\s*["\']?([\w.-]+)', prefix, re.I)
    encoding = header[1] if header else document[1] if document else 'utf-8'
    try:
        codecs.lookup(encoding)
        return body.decode(encoding, errors='replace').lstrip('\ufeff')
    except (LookupError, ValueError):
        raise FetchError('unsupported_charset') from None


class Fetcher:
    def __init__(self, sources, session=None):
        self.hosts = {urlsplit(s['url']).hostname for s in sources if s.get('research_enabled')}
        self.session = session or requests.Session()
        if session is None:
            self.session.trust_env = False
        self.robots = {}
        self.last = {}
        self.timeouts={urlsplit(s['url']).hostname:(
            min(15,max(8,s.get('connect_timeout_seconds',8))),
            min(45,max(20,s.get('read_timeout_seconds',20))))
            for s in sources if s.get('research_enabled')}
        self.timeout_retries={urlsplit(s['url']).hostname:min(1,max(0,s.get('timeout_retries',0)))
                              for s in sources if s.get('research_enabled')}

    def _request(self, url, delay=1):
        url = safe_url(url, self.hosts)
        host = urlsplit(url).hostname
        pause = max(0, delay - (time.monotonic() - self.last.get(host, 0)))
        if pause:
            time.sleep(pause)
        self.last[host] = time.monotonic()
        response = self.session.get(url, timeout=self.timeouts[host], stream=True,
                                    allow_redirects=False, headers={'User-Agent': AGENT})
        try:
            if response.is_redirect:
                return None, safe_url(urljoin(url, response.headers['Location']), self.hosts)
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise FetchError('response_too_large')
            return decode(bytes(body), response.headers.get('Content-Type', '')), None
        finally:
            response.close()

    def _rules(self, host):
        if host not in self.robots:
            url = f'https://{host}/robots.txt'
            # Fail closed on errors, missing files, or a cross-host robots redirect.
            for _ in range(5):
                body, redirect = self._request(url)
                if redirect:
                    if urlsplit(redirect).hostname != host:
                        raise FetchError('robots_redirect_not_approved')
                    url = redirect
                    continue
                robot = RobotFileParser()
                robot.parse(body.splitlines())
                self.robots[host] = robot
                break
            else:
                raise FetchError('robots_redirect_limit')
        return self.robots[host]

    def get(self, url):
        try:
            return self._get_once(url)
        except requests.Timeout:
            host=urlsplit(url).hostname
            if self.timeout_retries.get(host,0)<=0:raise
            self.timeout_retries[host]-=1
            time.sleep(2)
            return self._get_once(url)

    def _get_once(self, url):
        for _ in range(5):
            url = safe_url(url, self.hosts)
            rules = self._rules(urlsplit(url).hostname)
            if not rules.can_fetch(AGENT, url):
                raise FetchError('robots_disallowed')
            delay = max(1, rules.crawl_delay(AGENT) or rules.crawl_delay('*') or 1)
            rate = rules.request_rate(AGENT) or rules.request_rate('*')
            if rate and rate.requests:
                delay = max(delay, rate.seconds / rate.requests)
            if delay > 60:
                raise FetchError('crawl_delay_exceeds_budget')
            body, redirect = self._request(url, delay)
            if not redirect:
                return body, url
            url = redirect
        raise FetchError('redirect_limit')


def error_code(exc):
    if isinstance(exc, FetchError):
        return str(exc)
    if isinstance(exc, requests.exceptions.SSLError):
        return 'tls_failed'
    if isinstance(exc, requests.HTTPError):
        return f'http_{exc.response.status_code}' if exc.response is not None else 'http_failed'
    if isinstance(exc, requests.Timeout):
        return 'timeout'
    if isinstance(exc, requests.ConnectionError):
        return 'connection_failed'
    return 'reader_failed'
