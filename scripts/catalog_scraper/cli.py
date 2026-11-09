"""Command-line interface for the continuing-education catalog scraper."""

import argparse
import sys

from .catalog_scraper import CatalogScraper
from .settings import MAX_PAGES_PER_PROVIDER, MAX_WORKERS, OUTPUT_PATH, REPORT_PATH


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="generated catalog JSON path")
    parser.add_argument("--report", default=str(REPORT_PATH), help="crawl report JSON path")
    parser.add_argument("--max-providers", type=int, default=0, help="limit providers for a short test run")
    parser.add_argument("--provider-domain", help="scan one registered provider domain, e.g. supsi.ch")
    parser.add_argument("--max-pages-per-provider", type=int, default=MAX_PAGES_PER_PROVIDER)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        CatalogScraper(args.output, args.report, args.max_providers, args.provider_domain, args.max_pages_per_provider, args.workers).run()
    except Exception as error:
        print("Scrape failed: {}".format(error), file=sys.stderr)
        return 1
    return 0
