"""Rate-limited HTTP client that honors each provider's robots.txt."""

import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from .settings import REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT, USER_AGENT
from .text_utils import is_same_institution, normalize_url

class PoliteFetcher:
    def __init__(self, domain, delay=REQUEST_DELAY_SECONDS):
        self.domain = domain
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"})
        self.last_request = 0.0
        self.robots = {}
        self.pages_fetched = 0
        self.failures = []
        self.denied = 0

    def _wait(self, extra_delay=0.0):
        delay = max(self.delay, extra_delay)
        remaining = delay - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)
        self.last_request = time.monotonic()

    def _robots_for(self, url):
        host = (urlsplit(url).hostname or "").lower()
        if host in self.robots:
            return self.robots[host]
        robots_url = "https://{}/robots.txt".format(host)
        parser = RobotFileParser()
        parser.set_url(robots_url)
        self._wait()
        try:
            response = self.session.get(robots_url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 403:
                parser.parse(["User-agent: *", "Disallow: /"])
            elif response.status_code < 400:
                parser.parse(response.text.splitlines())
            else:
                # Missing robots.txt is treated as no published restriction.
                parser.parse([])
        except requests.RequestException:
            parser.parse([])
        self.robots[host] = parser
        return parser

    def get(self, url):
        if not is_same_institution(url, self.domain):
            return None, "outside institution domain"
        parser = self._robots_for(url)
        try:
            if not parser.can_fetch(USER_AGENT, url):
                self.denied += 1
                return None, "disallowed by robots.txt"
        except Exception:
            pass
        crawl_delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0
        self._wait(float(crawl_delay))
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if response.status_code >= 400:
                self.failures.append("{} returned {}".format(url, response.status_code))
                return None, "HTTP {}".format(response.status_code)
            final_url = normalize_url(response.url)
            if not final_url or not is_same_institution(final_url, self.domain):
                return None, "redirected outside institution domain"
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not any(kind in content_type for kind in ("html", "xml", "text/plain", "octet-stream")):
                return None, "non-document content type"
            if len(response.content) > 8_000_000:
                return None, "document too large"
            self.pages_fetched += 1
            return response, None
        except requests.RequestException as error:
            self.failures.append("{}: {}".format(url, error.__class__.__name__))
            return None, error.__class__.__name__

    def post_json(self, url, payload, referer=None):
        """POST a same-provider JSON pagination request while honoring robots and pacing."""
        if not is_same_institution(url, self.domain):
            return None, "outside institution domain"
        parser = self._robots_for(url)
        try:
            if not parser.can_fetch(USER_AGENT, url):
                self.denied += 1
                return None, "disallowed by robots.txt"
        except Exception:
            pass
        crawl_delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0
        self._wait(float(crawl_delay))
        try:
            response = self.session.post(
                url,
                json=payload,
                headers={"X-Requested-With": "XMLHttpRequest", "Referer": referer or url, "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code >= 400:
                self.failures.append("{} returned {}".format(url, response.status_code))
                return None, "HTTP {}".format(response.status_code)
            if not is_same_institution(normalize_url(response.url) or "", self.domain):
                return None, "redirected outside institution domain"
            if len(response.content) > 8_000_000:
                return None, "response too large"
            self.pages_fetched += 1
            return response, None
        except requests.RequestException as error:
            self.failures.append("{}: {}".format(url, error.__class__.__name__))
            return None, error.__class__.__name__
