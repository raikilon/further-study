import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catalog_scraper.pagination_adapters import HtmlPaginationAdapter, SearchResultsWidgetAdapter
from catalog_scraper.program_parser import ProgramParser


class FakeJsonResponse:
    def __init__(self, value):
        self.value = value

    def json(self):
        return self.value


class FakeSearchFetcher:
    def __init__(self):
        self.requests = []

    def post_json(self, url, payload, referer=None):
        self.requests.append((url, payload, referer))
        pages = [
            {
                "moreResultsButton": True,
                "totalCount": 2,
                "resultsGridHtml": '<li class="search-result-item"><a href="/en/continuing-education/cas/bfh-data"><h2>CAS Data Analytics</h2><p>Learn to work with data.</p></a></li>',
            },
            {
                "moreResultsButton": False,
                "totalCount": 2,
                "resultsGridHtml": '<li class="search-result-item"><a href="/en/continuing-education/cas/bfh-leadership"><h2>CAS Leadership</h2><p>Develop leadership skills.</p></a></li>',
            },
        ]
        return FakeJsonResponse(pages[len(self.requests) - 1]), None


class HtmlPaginationAdapterTest(unittest.TestCase):
    def test_detects_and_follows_standard_next_and_numbered_page_links(self):
        soup = BeautifulSoup(
            """
            <nav class="pagination" aria-label="Course pages">
              <a href="?page=1">1</a>
              <a rel="next" href="?page=2">Next</a>
            </nav>
            """,
            "html.parser",
        )
        adapter = HtmlPaginationAdapter()

        findings = adapter.inspect(soup, "https://example.ch/continuing-education")
        links = adapter.followable_links(soup, "https://example.ch/continuing-education", "example.ch")

        self.assertIn("next-link", {finding["kind"] for finding in findings})
        self.assertIn("numbered-page-link", {finding["kind"] for finding in findings})
        self.assertIn("https://example.ch/continuing-education?page=2", links)

    def test_marks_unwired_load_more_buttons_for_an_adapter(self):
        soup = BeautifulSoup('<button class="load-more">Show more programs</button>', "html.parser")
        findings = HtmlPaginationAdapter().inspect(soup, "https://example.ch/programs")

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["kind"], "load-more-button")
        self.assertEqual(findings[0]["status"], "adapter-required")

    def test_ignores_expandable_text_and_carousel_controls(self):
        soup = BeautifulSoup(
            """
            <div class="js-collapsed_text">
              <button class="js-collapsed_text--toggle">Mehr anzeigen Weniger anzeigen</button>
            </div>
            <div class="carousel">
              <a class="right carousel-control" href="#gallery" data-slide="next">Next</a>
            </div>
            <nav class="pagination">
              <a class="pagination-circle-button" href="#semester-2">2</a>
            </nav>
            <div class="cs2news-pagination pagination"><ul><li><a class="pagination-link" href="?page=2">2</a></li></ul></div>
            <a href="/details" class="more-link">En savoir plus</a>
            """,
            "html.parser",
        )

        self.assertEqual(HtmlPaginationAdapter().inspect(soup, "https://example.ch/programs"), [])

    def test_ignores_observed_non_catalog_expand_buttons(self):
        soup = BeautifulSoup(
            """
            <button aria-controls="long-description" aria-expanded="false">Mehr anzeigen</button>
            <button class="phzh-card-teaser-list__link">Mehr anzeigen</button>
            <button class="imd-custom-cards__show-more-bttn">Show more</button>
            """,
            "html.parser",
        )

        self.assertEqual(HtmlPaginationAdapter().inspect(soup, "https://example.ch/programs"), [])

    def test_search_results_widget_reads_multiple_json_pages(self):
        soup = BeautifulSoup(
            '<div class="comp-search-results" data-url="/en/search" data-state="{&quot;count&quot;: 1}"><button class="more-results-button">More results</button></div>',
            "html.parser",
        )
        fetcher = FakeSearchFetcher()
        adapter = SearchResultsWidgetAdapter(ProgramParser())
        provider = {"name": "BFH", "domain": "bfh.ch"}

        result = adapter.load_more(soup, "https://bfh.ch/en/continuing-education/cas", provider, fetcher, 3)

        self.assertEqual(result.pages_loaded, 2)
        self.assertEqual([program["title"] for program in result.programs], ["CAS Data Analytics", "CAS Leadership"])
        self.assertEqual(fetcher.requests[0][1]["offset"], 1)


if __name__ == "__main__":
    unittest.main()
