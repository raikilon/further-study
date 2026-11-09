import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catalog_scraper.pagination_adapters import SupsiWidgetPaginationAdapter
from catalog_scraper.program_parser import ProgramParser


COURSE_CARD = """
<div class="corso">
  <h3>CAS Intelligenza Artificiale applicata al processo di trasformazione digitale</h3>
  <div><h5>Data inizio</h5><p>02 febbraio 2027</p></div>
  <div><h5>Erogazione</h5><p>Modalità blended</p></div>
  <div><h5>ECTS</h5><p>14</p></div>
  <a href="/it/course-details?id=1997-cas-intelligenza-artificiale-applicata-processo-trasformazione-digitale"></a>
</div>
"""


class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "text/html"}

    def __init__(self, content):
        self.content = content.encode("utf-8")


class FakeFetcher:
    domain = "supsi.ch"

    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if "first-widget" in url:
            return FakeResponse('<div class="corso"><h3>Short course without a CAS</h3></div>'), None
        if "second-widget" in url and ("page%3D1" in url or "page=1" in url):
            return FakeResponse(COURSE_CARD), None
        return FakeResponse("<html><body></body></html>"), None


class SupsiPaginationTest(unittest.TestCase):
    def test_load_more_adapter_checks_widgets_in_page_order_and_finds_program(self):
        from bs4 import BeautifulSoup

        catalog = BeautifulSoup(
            '<div data-widget-id="first-widget"><a class="load-more-items" href="#">More</a></div>'
            '<div data-widget-id="second-widget"><a class="load-more-items" href="#">More</a></div>',
            "html.parser",
        )
        fetcher = FakeFetcher()
        provider = {"name": "SUPSI", "domain": "supsi.ch"}
        adapter = SupsiWidgetPaginationAdapter(ProgramParser())

        batch = adapter.load_more(
            catalog,
            "https://formazionecontinua.supsi.ch/it/catalogocorsi",
            provider,
            fetcher,
            max_pages=5,
        )

        self.assertEqual(batch.pages_loaded, 3)
        self.assertEqual(len(batch.programs), 1)
        program = batch.programs[0]
        self.assertEqual(program["title"], "CAS Intelligenza Artificiale applicata al processo di trasformazione digitale")
        self.assertEqual(program["nextStart"], "2027-02-02")
        self.assertEqual(program["ects"], 14.0)
        self.assertEqual(program["format"], "hybrid")
        self.assertTrue(program["sourceUrl"].endswith("id=1997-cas-intelligenza-artificiale-applicata-processo-trasformazione-digitale"))
        self.assertIn("second-widget", fetcher.urls[1])


if __name__ == "__main__":
    unittest.main()
