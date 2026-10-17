from copy import deepcopy
import unittest
from camper_pipeline import evaluate, report_selection
from report_html import render_html
from search_assessment import assess
import test_camper_pipeline as fixtures


class SearchShortlistTests(unittest.TestCase):
    def candidate(self):
        c = fixtures.ScreeningTests().example()
        c.update(price_incl_vat=6500, distance_km=40)
        c.pop("independent_review")
        c.pop("conversion_assessment")
        c["checks"]["conversion_suitable"] = None
        return c

    def evaluate(self, c):
        return evaluate({"candidates": [c]}, lambda plate: {"vehicle": {"status": "ok", "records": [{"kenteken": plate}]}})

    def test_search_match_does_not_require_contact_or_inspection(self):
        result = self.evaluate(self.candidate())
        item = result["results"][0]
        self.assertTrue(item["search_assessment"]["matched"])
        self.assertFalse(item["qualified"])
        self.assertEqual(result["search_matches"], 1)
        self.assertEqual(result["purchase_ready"], 0)
        self.assertEqual(len(report_selection(result)["potential"]), 1)
        html = render_html(result)
        self.assertIn("1 zoekmatches", html)
        self.assertIn("aankoopkeuring volgt", html)

    def test_any_hard_failure_wins_over_high_evidence(self):
        for field, value in (("price_incl_vat", 9000), ("distance_km", 101)):
            c = self.candidate()
            c[field] = value
            self.assertEqual(self.evaluate(c)["results"][0]["search_assessment"]["status"], "REJECTED")
        for check in ("cab_ac", "conversion_suitable", "high_roof"):
            c = self.candidate()
            c["checks"][check] = False
            self.assertFalse(self.evaluate(c)["results"][0]["search_assessment"]["matched"])

    def test_partial_roof_price_route_is_conditional_not_a_pass(self):
        c = self.candidate()
        c["checks"]["high_roof"] = None
        result = self.evaluate(c)
        self.assertEqual(result["results"][0]["search_assessment"]["status"], "CONDITIONAL")
        self.assertFalse(result["results"][0]["search_assessment"]["matched"])
        c["price_incl_vat"] = None
        c["distance_km"] = None
        c["checks"].update(high_roof=True, cab_ac=True)
        self.assertFalse(self.evaluate(c)["results"][0]["search_assessment"]["matched"])

    def test_rss_or_unbound_records_never_become_search_matches(self):
        c = self.candidate()
        c["individual_listing_confirmed"] = False
        self.assertFalse(self.evaluate(c)["results"][0]["search_assessment"]["matched"])
        self.assertEqual(evaluate({"candidates": [], "unverified_rss_leads": [{"title": "Van"}]})["search_matches"], 0)

    def test_explicit_sold_status_rejects_without_demanding_seller_contact(self):
        c = self.candidate()
        c["field_evidence"] = {"seller_reported":[{"seller_reported_availability":"Sold"}]}
        self.assertFalse(self.evaluate(c)["results"][0]["search_assessment"]["matched"])
        c["field_evidence"]["seller_reported"][0]["seller_reported_availability"] = "Active"
        self.assertTrue(self.evaluate(c)["results"][0]["search_assessment"]["matched"])
