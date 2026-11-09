"""Merges catalog snapshots and atomically writes public JSON files."""

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from .settings import PROVIDER_NAME_OVERRIDES
from .text_utils import atomic_json, program_identity, program_quality, read_existing, root_domain, source_key
from .program_parser import is_non_program_record


class CatalogRepository:
    """Own catalog persistence, deduplication, and last-known-good merging."""

    def __init__(self, catalog_path, report_path):
        self.catalog_path = Path(catalog_path)
        self.report_path = Path(report_path)

    def merge(self, crawl_results):
        scraped = self._deduplicate_crawled(crawl_results)
        if not scraped:
            raise RuntimeError("The scrape discovered no program pages; keeping the last known catalog unchanged.")

        merged = dict(scraped)
        self._preserve_last_known(merged, crawl_results)
        catalog = sorted(merged.values(), key=lambda program: (program.get("title", "").lower(), program.get("provider", "").lower()))
        return catalog, len(scraped)

    @staticmethod
    def _deduplicate_crawled(crawl_results):
        scraped = {}
        source_index = {}
        for result in crawl_results:
            for program in result["programs"]:
                source = source_key(program["sourceUrl"])
                identity = source_index.get(source, program_identity(program))
                current = scraped.get(identity)
                if current is None or program_quality(program) > program_quality(current):
                    scraped[identity] = program
                source_index[source] = identity
        return scraped

    def _preserve_last_known(self, merged, crawl_results):
        merged_sources = {source_key(program.get("sourceUrl", "")) for program in merged.values() if program.get("sourceUrl")}
        scanned_domains = {result["provider"]["domain"] for result in crawl_results if result["pagesFetched"] > 0}
        for program in self.load():
            source = program.get("sourceUrl")
            identity = program_identity(program)
            normalized_source = source_key(source) if source else None
            old_domain = program.get("providerDomain") or root_domain(urlsplit(source or "").hostname or "")
            if program.get("confidence") == "low" and old_domain in scanned_domains:
                continue
            if not source or identity in merged or normalized_source in merged_sources or is_non_program_record(program):
                continue
            preserved = dict(program)
            if old_domain in PROVIDER_NAME_OVERRIDES:
                preserved["provider"] = PROVIDER_NAME_OVERRIDES[old_domain]
                preserved["providerDomain"] = old_domain
            if old_domain in scanned_domains:
                preserved["catalogStatus"] = "not-reconfirmed"
            merged[identity] = preserved
            merged_sources.add(normalized_source)

    def load(self):
        return read_existing(self.catalog_path)

    def save(self, catalog, report):
        atomic_json(self.catalog_path, catalog)
        atomic_json(self.report_path, report)

    @staticmethod
    def build_report(directory_source, discovered, crawl_results, found_count):
        providers = []
        for result in crawl_results:
            providers.append({
                "name": result["provider"]["name"],
                "domain": result["provider"]["domain"],
                "status": result["status"],
                "pagesFetched": result["pagesFetched"],
                "paginationPagesFetched": result["paginationPagesFetched"],
                "paginationAdapters": result["paginationAdapters"],
                "paginationFindings": result["paginationFindings"],
                "robotsDenied": result["robotsDenied"],
                "programsFound": len(result["programs"]),
                "note": result["note"],
            })
        return {
            "generatedAt": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "directorySource": directory_source,
            "institutionsDiscovered": len(discovered),
            "institutionsScanned": len(crawl_results),
            "pagesFetched": sum(result["pagesFetched"] for result in crawl_results),
            "paginationPagesFetched": sum(result["paginationPagesFetched"] for result in crawl_results),
            "paginationFindings": [
                {"provider": result["provider"]["name"], "domain": result["provider"]["domain"], **finding}
                for result in crawl_results
                for finding in result["paginationFindings"]
            ],
            "programsFound": found_count,
            "partial": sum(result["status"] == "partial" for result in crawl_results),
            "failures": sum(result["status"] in {"blocked", "error"} for result in crawl_results),
            "providers": providers,
        }
