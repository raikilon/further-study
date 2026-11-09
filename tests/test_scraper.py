import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catalog_scraper import program_parser, text_utils
from catalog_scraper.institution_directory import SwissuniversitiesDirectory


class ProgramExtractionTest(unittest.TestCase):
    def setUp(self):
        self.provider = {"name": "Example University", "domain": "example.ch", "homepage": "https://example.ch"}

    def test_extracts_program_fields_from_official_program_page(self):
        html = """
        <html lang="de"><head><title>CAS Sustainable Systems</title>
        <meta name="description" content="A practical certificate for sustainability professionals and leaders."></head>
        <body><main><h1>CAS Sustainable Systems</h1>
        <p>Develop the skills to lead sustainable change in your organisation.</p>
        <table>
          <tr><th>Unterrichtssprache</th><td>Deutsch / Englisch</td></tr>
          <tr><th>Standort</th><td>Bern</td></tr>
          <tr><th>Dauer</th><td>8 months</td></tr>
          <tr><th>Kosten</th><td>CHF 12'500</td></tr>
          <tr><th>Start</th><td>10.03.2027</td></tr>
          <tr><th>Credits</th><td>12 ECTS</td></tr>
        </table></main></body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        program = program_parser.ProgramParser.parse_page(soup, "https://example.ch/weiterbildung/cas/sustainable-systems", self.provider)

        self.assertIsNotNone(program)
        self.assertEqual(program["credential"], "CAS")
        self.assertEqual(program["languages"], ["de", "en"])
        self.assertEqual(program["city"], "Bern")
        self.assertEqual(program["duration"], "8 months")
        self.assertEqual(program["priceCHF"], 12500)
        self.assertEqual(program["nextStart"], "2027-03-10")
        self.assertEqual(program["ects"], 12.0)
        self.assertEqual(program["subject"], "sustainability")
        self.assertTrue(program["sourceUrl"].startswith("https://example.ch/"))

    def test_rejects_zero_ects_values(self):
        self.assertIsNone(text_utils.extract_ects("MAS in Gregorian Chant — 0 ECTS"))

    def test_ignores_general_continuing_education_catalog_page(self):
        html = "<html><body><main><h1>Continuing Education CAS and MAS programs</h1><p>Browse all courses.</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        program = program_parser.ProgramParser.parse_page(soup, "https://example.ch/continuing-education/cas", self.provider)
        self.assertIsNone(program)

    def test_ignores_child_course_pages_under_an_mas_overview_url(self):
        html = "<html><body><main><h1>Archives</h1><p>This course is one module in an MAS program.</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        program = program_parser.ProgramParser.parse_page(soup, "https://example.ch/education/mba-mas-das/expertise/archives", self.provider)
        self.assertIsNone(program)

    def test_ignores_registration_forms_as_program_records(self):
        html = "<html><body><main><h1>CAS Sustainable Systems</h1><p>Registration form</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        program = program_parser.ProgramParser.parse_page(soup, "https://example.ch/imoniteur/registration", self.provider)
        self.assertIsNone(program)

    def test_normalizes_and_scores_official_catalog_links(self):
        url = text_utils.normalize_url("http://www.example.ch/de/weiterbildung/cas/?utm_source=test")
        self.assertEqual(url, "https://example.ch/de/weiterbildung/cas")
        self.assertGreaterEqual(program_parser.candidate_score(url, "CAS Sustainable Systems"), 12)

    def test_preserves_www_for_hosts_where_bare_host_fails(self):
        self.assertEqual(text_utils.normalize_url("https://www.phbern.ch/"), "https://www.phbern.ch/")
        self.assertEqual(text_utils.normalize_url("https://www.example.ch/"), "https://example.ch/")

    def test_keeps_government_subdomains_distinct(self):
        self.assertEqual(text_utils.root_domain("www.ehsm.admin.ch"), "ehsm.admin.ch")
        self.assertEqual(text_utils.root_domain("www.unibe.ch"), "unibe.ch")

    def test_accepts_verified_canonical_domains_for_directory_aliases(self):
        self.assertTrue(text_utils.is_same_institution("https://www.usi.ch/it", "unisi.ch"))
        self.assertTrue(text_utils.is_same_institution("https://edhea.ch/", "ecav.ch"))
        self.assertTrue(text_utils.is_same_institution("https://www.sfuvet.swiss/", "sfivet.swiss"))
        self.assertFalse(text_utils.is_same_institution("https://not-usi.ch/", "unisi.ch"))

    def test_applies_verified_homepages_and_skips_unreachable_directory_site(self):
        eesp = BeautifulSoup('<a href="https://eesp.ch/">EESP</a>', "html.parser").a
        phbern = BeautifulSoup('<a href="https://phbern.ch/">PHBern</a>', "html.parser").a
        he_arc = BeautifulSoup('<a href="https://he-arc.ch/">HE-Arc</a>', "html.parser").a

        self.assertEqual(
            SwissuniversitiesDirectory._provider_from_link(eesp),
            {"name": "EESP", "domain": "eesp.ch", "homepage": "https://www.hetsl.ch/"},
        )
        self.assertEqual(
            SwissuniversitiesDirectory._provider_from_link(phbern)["homepage"],
            "https://www.phbern.ch/",
        )
        self.assertIsNone(SwissuniversitiesDirectory._provider_from_link(he_arc))

    def test_extracts_a_partial_catalog_listing_without_visiting_the_detail_page(self):
        html = """
        <html><body><main><article class="program-card">
          <a href="/weiterbildung/cas/digital-skills">CAS Digital Skills</a>
          <p>Develop practical skills in data analysis and digital transformation.</p>
        </article></main></body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        anchor = soup.select_one("a")
        program = program_parser.ProgramParser.parse_catalog_link(anchor, "https://example.ch/weiterbildung/", self.provider)
        self.assertIsNotNone(program)
        self.assertEqual(program["title"], "CAS Digital Skills")
        self.assertEqual(program["confidence"], "low")
        self.assertEqual(program["sourceUrl"], "https://example.ch/weiterbildung/cas/digital-skills")

    def test_extracts_metadata_from_supsi_catalog_card_links(self):
        html = """
        <div class="corso d-flex">
          <div class="left"><h3>CAS Intelligenza Artificiale applicata al processo di trasformazione digitale</h3></div>
          <div class="right">
            <div class="overview-item"><h5>Data inizio</h5><p>02 febbraio 2027</p></div>
            <div class="overview-item"><h5>Erogazione</h5><p>Modalità blended</p></div>
            <div class="overview-item"><h5>ECTS</h5><p>14</p></div>
          </div>
          <a href="/it/course-details?id=1997-cas-intelligenza-artificiale-applicata-processo-trasformazione-digitale"></a>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        card_link = soup.select_one("a[href]")
        program = program_parser.ProgramParser.parse_catalog_link(
            card_link,
            "https://formazionecontinua.supsi.ch/api/widgets/it/widget?page=13",
            {"name": "SUPSI", "domain": "supsi.ch"},
        )

        self.assertIsNotNone(program)
        self.assertEqual(program["title"], "CAS Intelligenza Artificiale applicata al processo di trasformazione digitale")
        self.assertEqual(program["nextStart"], "2027-02-02")
        self.assertEqual(program["ects"], 14.0)
        self.assertEqual(program["format"], "hybrid")


if __name__ == "__main__":
    unittest.main()
