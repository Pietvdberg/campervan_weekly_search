import unittest
from email.message import EmailMessage
from camper_pipeline import evaluate
from report_html import render_html

class HtmlReportTests(unittest.TestCase):
    def test_html_escapes_untrusted_titles_and_renders_links(self):
        candidate={
            "name":"Boxer <script>alert(1)</script> L2H2 airco",
            "source":"Marktplaats","listing_url":"https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123",
            "individual_listing_confirmed":True,
            "price_advertised":"7.000","price_incl_vat":None,"vat_basis":"unknown",
            "distance_km":None,"plate":None,"plate_confirmed_from_listing":False,
            "checks":{"high_roof":True,"cab_ac":True,"conversion_suitable":None,
                      "distance_within_100km":None,"price_incl_vat_within_8000":None}}
        result=evaluate({"candidates":[candidate]})
        html=render_html(result)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>alert(1)</script>",html)
        self.assertIn("https://www.marktplaats.nl/v/",html)
        self.assertIn("Niet bevestigd",html)
        self.assertIn("Niet geverifieerd",html)
        message=EmailMessage()
        message.set_content("Plain-text fallback")
        message.add_alternative(html,subtype="html")
        self.assertEqual(len(message.get_payload()),2)

    def test_html_rss_is_never_qualified(self):
        lead={"url":"https://www.autowereld.nl/renault/master/l2h2-123/details.html",
              "title":"Master L2H2 airco","description":"Vraagprijs: € 7.200"}
        result=evaluate({"candidates":[],"unverified_rss_leads":[lead]})
        html=render_html(result)
        self.assertIn("0 bevestigde matches",html)
        self.assertIn("Master L2H2 airco",html)
        self.assertIn("uitsluitend uit de externe RSS-index",html)

if __name__=="__main__":
    unittest.main()

class ReportConsistencyTests(unittest.TestCase):
    def fixture(self):
        from test_camper_pipeline import ScreeningTests
        return ScreeningTests().example()

    def evaluate(self, candidates, success=True):
        return evaluate({"candidates": candidates}, lambda plate: {"vehicle": {"status": "ok" if success else "error", "records": [{"kenteken": plate}] if success else []}})

    def test_qualified_html_has_no_contradictory_zero_match_claim(self):
        result = self.evaluate([self.fixture()])
        html = render_html(result)
        self.assertIn("1 bevestigde matches", html)
        self.assertNotIn("Er is nog geen voertuig", html)

    def test_rdws_blocker_is_visible_in_html(self):
        result = self.evaluate([self.fixture()], success=False)
        html = render_html(result)
        self.assertIn("RDW registration not verified", html)
        self.assertIn("0 bevestigde matches", html)

    def test_duplicate_count_and_selection_agree_across_formats(self):
        from camper_pipeline import report, report_selection
        weak = self.fixture()
        weak["checks"]["conversion_suitable"] = None
        strong = self.fixture()
        result = self.evaluate([weak, strong, strong])
        selection = report_selection(result)
        self.assertEqual(len(selection["qualified"]), 1)
        self.assertEqual(len(selection["potential"]), 0)
        self.assertEqual(len(result["results"]), 3)
        self.assertIn("Verified >=90% qualifiers: 1", report(result))
        self.assertIn("1 bevestigde matches", render_html(result))
        self.assertEqual(report(result).count("  Listing: "), 1)
