"""Reads XML sitemaps and returns same-provider URLs."""

import gzip
import re
import xml.etree.ElementTree as ET

from .settings import MAX_SITEMAP_LOCATIONS
from .text_utils import clean_text, is_same_institution, normalize_url


class SitemapReader:
    """Find and parse a provider's sitemap documents."""

    MAX_SITEMAP_FILES = 8

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def locations(self):
        pending = self._sitemaps_from_robots()
        pending.update(self._default_sitemaps())
        visited = set()
        locations = []

        while pending and len(visited) < self.MAX_SITEMAP_FILES and len(locations) < MAX_SITEMAP_LOCATIONS:
            sitemap_url = pending.pop()
            if not self._can_read(sitemap_url, visited):
                continue
            visited.add(sitemap_url)
            kind, sitemap_locations = self._read_sitemap(sitemap_url)
            if kind == "index":
                self._add_child_sitemaps(pending, sitemap_locations, visited)
            else:
                locations.extend(self._provider_locations(sitemap_locations))
        return locations[:MAX_SITEMAP_LOCATIONS]

    def _sitemaps_from_robots(self):
        robots_url = "https://{}/robots.txt".format(self.fetcher.domain)
        response, _ = self.fetcher.get(robots_url)
        if response is None:
            return set()
        sitemap_urls = set()
        for line in response.text.splitlines():
            match = re.match(r"\s*sitemap:\s*(\S+)", line, re.I)
            if match:
                sitemap_urls.add(normalize_url(match.group(1)))
        return sitemap_urls

    def _default_sitemaps(self):
        return {
            "https://{}/sitemap.xml".format(self.fetcher.domain),
            "https://{}/sitemap_index.xml".format(self.fetcher.domain),
        }

    def _can_read(self, url, visited):
        return bool(url and url not in visited and is_same_institution(url, self.fetcher.domain))

    def _read_sitemap(self, url):
        response, _ = self.fetcher.get(url)
        if response is None:
            return None, []
        body = response.content
        if url.endswith(".gz") or body[:2] == b"\x1f\x8b":
            try:
                body = gzip.decompress(body)
            except OSError:
                return None, []
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            return None, []
        kind = "index" if root.tag.rsplit("}", 1)[-1].lower() == "sitemapindex" else "urlset"
        locations = [clean_text(node.text) for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() == "loc" and node.text]
        return kind, locations

    def _add_child_sitemaps(self, pending, locations, visited):
        for location in locations:
            if len(pending) + len(visited) >= self.MAX_SITEMAP_FILES:
                return
            normalized = normalize_url(location)
            if self._can_read(normalized, visited):
                pending.add(normalized)

    def _provider_locations(self, locations):
        return [
            normalized
            for location in locations
            if (normalized := normalize_url(location)) and is_same_institution(normalized, self.fetcher.domain)
        ]
