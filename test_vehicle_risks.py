from datetime import date
import unittest

from camper_pipeline import evaluate, report, rss_shortlist
from report_html import render_html
from vehicle_risks import auction_evidence, rdw_risks


class VehicleRiskTests(unittest.TestCase):
    def fixture(self):
        from test_camper_pipeline import ScreeningTests
        return ScreeningTests().example()

    def test_expiry_boundary_and_odometer_assessment(self):
        risks = rdw_risks({"vervaldatum_apk": "20261016", "tellerstandoordeel": "Onlogisch"}, date(2026, 10, 17))
        self.assertEqual({risk["code"] for risk in risks}, {"apk_expired", "odometer_inconsistent"})
        self.assertTrue(all(risk["blocks_qualification"] for risk in risks))
        self.assertEqual(rdw_risks({"vervaldatum_apk": "20261017"}, date(2026, 10, 17)), [])

    def test_category_b_mass_limit_blocks_qualification_without_inventing_payload(self):
        risks = rdw_risks({"toegestane_maximum_massa_voertuig": "5000", "massa_ledig_voertuig": "2000"})
        self.assertEqual(risks[0]["code"], "licence_mass_review")
        self.assertTrue(risks[0]["blocks_qualification"])
        self.assertNotIn("payload", risks[0])

    def test_unknown_malformed_or_missing_data_is_not_a_clean_inspection(self):
        risks = rdw_risks({"vervaldatum_apk": "invalid", "tellerstandoordeel": "Geen oordeel"})
        self.assertEqual(risks[0]["code"], "apk_date_unverified")
        self.assertFalse(risks[0]["blocks_qualification"])

    def test_adverse_rdw_evidence_blocks_recommendation_and_is_visible(self):
        for fields in ({"tellerstandoordeel": "Onlogisch"}, {"vervaldatum_apk": "20000101"}):
            data = evaluate({"candidates": [self.fixture()]}, lambda plate: {"vehicle": {"status": "ok", "records": [{"kenteken": plate, **fields}]}})
            self.assertEqual(data["qualifiers"], 0)
            self.assertTrue(data["results"][0]["rdw_risks"])
            self.assertIn("RDW", report(data))
            self.assertIn("RDW-aandachtspunten", render_html(data))

    def test_auction_or_excluded_source_never_calls_rdw(self):
        for override in ({"name": "Peugeot Boxer L2H2 veiling"}, {"sale_method": "auction"},
                         {"listing_url": "https://www.bedrijfsauto.nl/peugeot-boxer-1234567"}):
            candidate = {**self.fixture(), **override}
            result = evaluate({"candidates": [candidate]}, lambda _: self.fail("Excluded sale must not trigger RDW"))
            self.assertEqual(result["qualifiers"], 0)
            self.assertEqual(result["results"][0]["rdw"], None)
            self.assertNotIn(candidate["name"], report(result))

    def test_negated_auction_text_is_not_auction_evidence(self):
        self.assertFalse(auction_evidence("Geen veiling, gewone verkoop"))
        self.assertFalse(auction_evidence("Niet via veiling verkocht"))
        self.assertTrue(auction_evidence("Verkoop via online veiling"))

    def test_rss_auction_lead_is_excluded(self):
        lead = {"url": "https://www.autowereld.nl/peugeot/boxer/l2h2-123/details.html", "title": "Boxer L2H2 veiling", "description": "Vraagprijs: € 5000"}
        self.assertEqual(rss_shortlist([lead]), [])

    def test_current_failure_is_distinct_from_explicitly_repaired_history(self):
        from vehicle_risks import mechanical_failure
        self.assertIsNotNone(mechanical_failure("Motor defect, start niet"))
        self.assertIsNone(mechanical_failure("Motor defect geweest, inmiddels gerepareerd"))
        self.assertIsNone(mechanical_failure("Geen schadeauto"))
        self.assertIsNone(mechanical_failure("Geadverteerde schadeauto- of occasionprijs"))
        self.assertIsNone(mechanical_failure("Garantie uitgesloten bij motor defect"))
        candidate = self.fixture()
        candidate["reported_mechanical_failure"] = "start niet"
        result = evaluate({"candidates": [candidate]}, lambda _: self.fail("Do not recommend or query a known non-runner"))
        self.assertEqual(result["qualifiers"], 0)
