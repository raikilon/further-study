"""Orchestrates provider discovery, crawling, and catalog publication."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from .catalog_repository import CatalogRepository
from .institution_crawler import InstitutionCrawler
from .institution_directory import SwissuniversitiesDirectory
from .settings import DIRECTORY_URL, MAX_PAGES_PER_PROVIDER, MAX_WORKERS, OUTPUT_PATH, REPORT_PATH


class CatalogScraper:
    """Coordinate one complete scrape run; each dependency owns its own concern."""

    def __init__(self, output_path=OUTPUT_PATH, report_path=REPORT_PATH, max_providers=0, provider_domain=None, max_pages_per_provider=MAX_PAGES_PER_PROVIDER, workers=MAX_WORKERS):
        self.output_path = output_path
        self.report_path = report_path
        self.max_providers = max_providers
        self.provider_domain = provider_domain
        self.max_pages_per_provider = max_pages_per_provider
        self.workers = workers
        self.repository = CatalogRepository(output_path, report_path)

    def run(self):
        providers = self._discover_providers()
        results = self._crawl_providers(providers)
        catalog, found_count = self.repository.merge(results)
        report = self.repository.build_report(DIRECTORY_URL, providers, results, found_count)
        self.repository.save(catalog, report)
        self._print_summary(catalog, found_count, len(providers), report["pagesFetched"])

    def _discover_providers(self):
        providers = SwissuniversitiesDirectory().discover()
        if self.provider_domain:
            providers = [provider for provider in providers if provider["domain"] == self.provider_domain]
        if self.max_providers:
            providers = providers[:self.max_providers]
        if not providers:
            raise RuntimeError("No institution websites could be extracted from the swissuniversities directory.")
        return providers

    def _crawl_providers(self, providers):
        crawler = InstitutionCrawler(self.max_pages_per_provider)
        results = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(crawler.crawl, provider): provider for provider in providers}
            for future in as_completed(futures):
                provider = futures[future]
                try:
                    results.append(future.result())
                except Exception as error:
                    results.append({
                        "provider": provider,
                        "programs": [],
                        "pagesFetched": 0,
                        "paginationPagesFetched": 0,
                        "paginationAdapters": [],
                        "paginationFindings": [],
                        "robotsDenied": 0,
                        "status": "error",
                        "note": error.__class__.__name__,
                    })
        return sorted(results, key=lambda result: result["provider"]["name"].lower())

    def _print_summary(self, catalog, found_count, institution_count, pages_fetched):
        print("Discovered {} programs from {} institutions ({} pages fetched).".format(found_count, institution_count, pages_fetched))
        print("Wrote {} catalog entries to {}".format(len(catalog), self.output_path))
        print("Wrote coverage report to {}".format(self.report_path))
