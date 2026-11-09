"""Loads recognized provider URLs from the Swissuniversities directory."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit

from .settings import DIRECTORY_URL, PROVIDER_HOMEPAGE_OVERRIDES, REQUEST_TIMEOUT, SKIP_ROOTS, USER_AGENT, PROVIDER_NAME_OVERRIDES
from .text_utils import clean_text, normalize_url, root_domain

class SwissuniversitiesDirectory:
    """Fetch and parse the official directory of recognized institutions."""

    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})

    def discover(self):
        response = self.session.get(DIRECTORY_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        content = BeautifulSoup(response.text, "html.parser")
        main = content.find(id="Content") or content.find("main") or content
        providers = {}

        for link in main.select("a[href]"):
            provider = self._provider_from_link(link)
            if provider and provider["domain"] not in providers:
                providers[provider["domain"]] = provider
        return list(providers.values())

    @staticmethod
    def _provider_from_link(link):
        url = normalize_url(link.get("href"), DIRECTORY_URL)
        if not url:
            return None
        domain = root_domain(urlsplit(url).hostname)
        directory_domain = root_domain(urlsplit(DIRECTORY_URL).hostname)
        if not domain or domain in SKIP_ROOTS or domain == directory_domain:
            return None

        name = clean_text(link.get_text(" ", strip=True) or link.get("title") or link.get("aria-label"))
        if not name or len(name) < 2 or name.lower() in {"home", "website", "visit website", "www"}:
            name = domain
        homepage = PROVIDER_HOMEPAGE_OVERRIDES.get(domain, url)
        return {"name": PROVIDER_NAME_OVERRIDES.get(domain, name), "domain": domain, "homepage": homepage}
