"""Crawls relevant program pages for one institution."""

import heapq
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .http_client import PoliteFetcher
from .pagination_adapters import HtmlPaginationAdapter, SearchResultsWidgetAdapter, SupsiWidgetPaginationAdapter
from .program_parser import ProgramParser, candidate_score, path_has_credential
from .settings import MAX_CANDIDATE_LINKS, MAX_PAGES_PER_PROVIDER, PROVIDER_START_PAGES
from .sitemap_reader import SitemapReader
from .text_utils import clean_text, is_same_institution, normalize_url, program_quality, source_key


class CandidateQueue:
    """Priority queue for same-provider catalog and credential links."""

    def __init__(self, domain):
        self.domain = domain
        self._items = []
        self._pending = set()

    def add(self, url, score, visited):
        normalized = normalize_url(url)
        if not normalized or score < 3 or not is_same_institution(normalized, self.domain):
            return
        if normalized in self._pending or normalized in visited:
            return
        heapq.heappush(self._items, (-score, normalized))
        self._pending.add(normalized)

    def pop(self):
        if not self._items:
            return None
        _, url = heapq.heappop(self._items)
        self._pending.discard(url)
        return url

    def trim(self, limit):
        if len(self._items) <= limit:
            return
        self._items = heapq.nsmallest(limit, self._items)
        heapq.heapify(self._items)
        self._pending = {url for _, url in self._items}

    def __bool__(self):
        return bool(self._items)


class InstitutionCrawler:
    """Own page traversal for one official institution domain."""

    def __init__(self, max_pages=MAX_PAGES_PER_PROVIDER, parser=None, fetcher_factory=PoliteFetcher):
        self.max_pages = max_pages
        self.parser = parser or ProgramParser()
        self.fetcher_factory = fetcher_factory
        self.html_pagination = HtmlPaginationAdapter()
        self.supsi_pagination = SupsiWidgetPaginationAdapter(self.parser)
        self.search_results_pagination = SearchResultsWidgetAdapter(self.parser)

    def crawl(self, provider):
        fetcher = self.fetcher_factory(provider["domain"])
        queue = CandidateQueue(provider["domain"])
        visited = set()
        programs = {}
        notes = []
        pagination_pages = 0
        pagination_adapters = set()
        pagination_findings = {}

        queue.add(provider["homepage"], 100, visited)
        for start_page in PROVIDER_START_PAGES.get(provider["domain"], ()):
            queue.add(start_page, 110, visited)
        self._add_sitemap_pages(queue, fetcher, visited)
        while queue and fetcher.pages_fetched < self.max_pages:
            page_url = queue.pop()
            if page_url in visited:
                continue
            visited.add(page_url)
            result = self._inspect_page(page_url, provider, fetcher)
            if result is None:
                continue
            if result["note"]:
                notes.append(result["note"])
            if result["soup"] is None:
                continue
            page_findings = self.html_pagination.inspect(result["soup"], result["pageUrl"])
            for finding in page_findings:
                pagination_findings[(finding["kind"], finding["url"])] = finding
            self._keep_better_program(programs, result["program"])
            self._queue_links(result["soup"], result["pageUrl"], provider, queue, visited, programs)
            pagination_result = self._load_more_pages(result["soup"], result["pageUrl"], provider, fetcher, queue, visited, programs)
            pagination_pages += pagination_result["pagesFetched"]
            if pagination_result["pagesFetched"]:
                pagination_adapters.add(pagination_result["adapter"])
                for finding in page_findings:
                    if finding["kind"] in {"load-more-link", "load-more-button"}:
                        finding["status"] = "expanded by {}".format(pagination_result["adapter"])
                pagination_findings[(pagination_result["adapter"], result["pageUrl"])] = {
                    "kind": pagination_result["adapter"],
                    "url": result["pageUrl"],
                    "status": "expanded",
                    "pagesFetched": pagination_result["pagesFetched"],
                }
            notes.extend(pagination_result["issues"])
            queue.trim(MAX_CANDIDATE_LINKS)

        for program in programs.values():
            program["provider"] = provider["name"]
        return self._crawl_result(provider, fetcher, programs, notes, pagination_pages, sorted(pagination_adapters), list(pagination_findings.values()))

    @staticmethod
    def _add_sitemap_pages(queue, fetcher, visited):
        for sitemap_url in SitemapReader(fetcher).locations():
            score = candidate_score(sitemap_url)
            if score >= 6:
                extra = 2 if path_has_credential(urlsplit(sitemap_url).path) else 0
                queue.add(sitemap_url, score + extra, visited)

    def _inspect_page(self, url, provider, fetcher):
        response, reason = fetcher.get(url)
        if response is None:
            if reason and reason not in {"outside institution domain", "non-document content type"}:
                return {"note": "{}: {}".format(url, reason), "soup": None}
            return {"note": None, "soup": None}

        content_type = response.headers.get("Content-Type", "").lower()
        if "xml" in content_type or "pdf" in content_type:
            return {"note": None, "soup": None}

        page_url = normalize_url(response.url) or url
        soup = BeautifulSoup(response.content, "html.parser")
        is_homepage = urlsplit(page_url).path in {"", "/"}
        provider["name"] = self.parser.provider_name(soup, provider["name"], is_homepage)
        program = self.parser.parse_page(soup, page_url, provider)
        return {"pageUrl": page_url, "soup": soup, "program": program, "note": None}

    def _queue_links(self, soup, page_url, provider, queue, visited, programs):
        for anchor in soup.select("a[href]"):
            href = normalize_url(anchor.get("href"), page_url)
            if not href or not is_same_institution(href, provider["domain"]):
                continue
            text = clean_text(anchor.get_text(" ", strip=True) or anchor.get("title") or anchor.get("aria-label"))
            score = candidate_score(href, text)
            is_next_page = self.html_pagination.is_next_page_link(anchor)
            is_page_number = self.html_pagination.is_page_number_link(anchor)
            is_load_more = self.html_pagination.is_load_more_control(anchor)
            if score < 3 and not (is_next_page or is_page_number or is_load_more):
                continue
            candidate = self.parser.parse_catalog_link(anchor, page_url, provider) if score >= 3 else None
            if candidate:
                self._keep_better_program(programs, candidate)
            pagination_score = 18 if is_next_page else (8 if is_page_number or is_load_more else 0)
            queue.add(href, max(score, pagination_score), visited)

        for pagination_url in self.html_pagination.followable_links(soup, page_url, provider["domain"]):
            queue.add(pagination_url, 18, visited)

    def _load_more_pages(self, soup, page_url, provider, fetcher, queue, visited, programs):
        remaining_pages = max(0, self.max_pages - fetcher.pages_fetched)
        if not remaining_pages:
            return {"adapter": None, "pagesFetched": 0, "issues": []}

        if self.supsi_pagination.supports(provider, soup, page_url):
            adapter_name, adapter = "supsi-widget", self.supsi_pagination
        elif self.search_results_pagination.supports(soup, page_url):
            adapter_name, adapter = "search-results-widget", self.search_results_pagination
        else:
            return {"adapter": None, "pagesFetched": 0, "issues": []}

        batch = adapter.load_more(soup, page_url, provider, fetcher, remaining_pages)
        for program in batch.programs:
            self._keep_better_program(programs, program)
        for detail_url in batch.detail_urls:
            queue.add(detail_url, candidate_score(detail_url), visited)
        return {"adapter": adapter_name, "pagesFetched": batch.pages_loaded, "issues": batch.issues}

    @staticmethod
    def _keep_better_program(programs, program):
        if not program:
            return
        source = source_key(program["sourceUrl"])
        current = programs.get(source)
        if current is None or program_quality(program) > program_quality(current):
            programs[source] = program

    @staticmethod
    def _crawl_result(provider, fetcher, programs, notes, pagination_pages, pagination_adapters, pagination_findings):
        if fetcher.pages_fetched == 0 and fetcher.denied:
            status = "blocked"
        elif fetcher.pages_fetched == 0:
            status = "error"
        elif fetcher.failures or fetcher.denied:
            status = "partial"
        else:
            status = "ok"
        return {
            "provider": provider,
            "programs": list(programs.values()),
            "pagesFetched": fetcher.pages_fetched,
            "paginationPagesFetched": pagination_pages,
            "paginationAdapters": pagination_adapters,
            "paginationFindings": pagination_findings,
            "robotsDenied": fetcher.denied,
            "status": status,
            "note": "; ".join(notes[:4]) if notes else None,
        }
