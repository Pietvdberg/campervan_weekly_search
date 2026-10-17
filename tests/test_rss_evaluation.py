import unittest
from copy import deepcopy

from campervan_search.camper_pipeline import evaluate, report
from campervan_search.coverage_report import render
from campervan_search.report_html import render_html
from campervan_search.rss_evaluation import evaluate_leads
from campervan_search.search_history import coverage_health


class RssEvaluationTests(unittest.TestCase):
    def lead(self, title="Peugeot Boxer L2H2 Airco", price="4.500", id=12345):
        return {
            "url": (
                (
                    "https://www.autowereld.nl/peugeot/boxer/"
                    "l2h2-"
                    f"{id}"
                    "/details.html"
                )
            ),
            "title": title,
            "description": f"<b>Vraagprijs</b>: € {price}<br>Bouwjaar: 2010",
        }

    def test_every_feed_record_gets_an_outcome(self):
        rows = [
            self.lead(id=1),
            self.lead(price="19.000", id=2),
            self.lead(title="Boxer L2H2", id=3),
            self.lead(title="Boxer L2H2 Airco motor niet %100", id=4),
        ]
        result = evaluate_leads(rows)
        self.assertEqual(result["evaluated_records"], 4)
        self.assertEqual(result["counts"]["INTERESTING"], 1)
        self.assertEqual(result["counts"]["EXCLUDED"], 2)
        self.assertEqual(result["counts"]["NEEDS_INFO"], 1)
        self.assertIsNone(
            result["shortlist"][0]["source_reported_gross_price"]
        )
        self.assertIsNone(result["shortlist"][0]["distance_km"])

    def test_feed_year_and_high_mileage_do_not_force_rejection(
        self,
    ):
        lead = self.lead()
        lead["description"] = (
            "<b>Vraagprijs</b>: € 3.750<br><b>Bouwjaar</b>:"
            " 2019<br><b>Kilometerstand</b>: 481.956 km"
        )
        row = evaluate_leads([lead])["shortlist"][0]
        self.assertEqual(row["source_reported_year"], 2019)
        self.assertEqual(row["source_reported_mileage_km"], 481956)
        self.assertEqual(row["status"], "INTERESTING")

    def test_vat_uncertainty_and_gross_scenario_are_explicit(self):
        row = evaluate_leads([self.lead(price="7.450")])["shortlist"][0]
        self.assertEqual(row["gross_if_21_percent_added"], 9014.5)
        self.assertIsNone(row["source_reported_gross_price"])
        self.assertIn("Btw is bepalend", row["questions"][0])
        lead = self.lead(price="7.000")
        lead["description"] += " excl btw"
        result = evaluate_leads([lead])
        self.assertEqual(result["counts"]["EXCLUDED"], 1)

    def test_retrofit_roof_requires_airco_and_no_current_faults(
        self,
    ):
        result = evaluate_leads(
            [
                self.lead(title="Boxer L1H1 Airco"),
                self.lead(title="Boxer L2H2 geen airco", id=2),
                self.lead(
                    title="Boxer L2H2 Airco motorstoringslampje brandt", id=3
                ),
            ]
        )
        self.assertEqual(result["counts"]["INTERESTING"], 1)
        row = result["shortlist"][0]
        self.assertTrue(row["low_roof_mentioned"])
        self.assertTrue(any("hefdak" in q for q in row["questions"]))
        self.assertEqual(result["counts"]["EXCLUDED"], 2)

    def test_duplicate_and_already_bound_urls_are_not_recommended_twice(self):
        lead = self.lead()
        result = evaluate_leads([lead, deepcopy(lead)], [lead["url"]])
        self.assertEqual(result["counts"]["ALREADY_EVALUATED"], 1)
        self.assertEqual(result["counts"]["DUPLICATE"], 1)
        self.assertEqual(result["shortlist"], [])

    def test_town_hints_do_not_create_road_evidence_or_qualified_matches(self):
        lead = self.lead(title="Boxer L2H2 Airco Roosendaal")
        data = evaluate({"unverified_rss_leads": [lead]})
        self.assertEqual(data["qualifiers"], 0)
        self.assertEqual(data["search_matches"], 0)
        row = data["rss_evaluation"]["shortlist"][0]
        self.assertEqual(row["place_hints_not_routes"], ["roosendaal"])
        self.assertIsNone(row["distance_km"])
        self.assertIn("Why investigate:", report(data))
        self.assertIn("Waarom onderzoeken:", render_html(data))
        self.assertIn("1 feeditems beoordeeld", render_html(data))

    def test_bad_urls_and_html_are_not_promoted(self):
        lead = self.lead(title="Boxer L2H2 Airco <script>alert(1)</script>")
        lead["url"] = "https://evil.example/van"
        self.assertEqual(evaluate_leads([lead])["shortlist"], [])
        lead["url"] = self.lead()["url"]
        self.assertNotIn(
            "<script>", render_html(evaluate({"unverified_rss_leads": [lead]}))
        )

    def test_validation_detects_lost_feed_records_and_invented_routes(self):
        from campervan_search.source_catalog import SOURCE_NAMES
        from campervan_search.validate_search import summarize

        discovery = {
            "unverified_rss_leads": [self.lead()],
            "source_coverage": {s: {} for s in SOURCE_NAMES},
        }
        data = evaluate(discovery)
        self.assertTrue(summarize(discovery, data)["validation_passed"])
        data["rss_evaluation"]["results"][0]["distance_km"] = 20
        self.assertIn(
            "RSS town hints must not create verified road distances",
            summarize(discovery, data)["errors"],
        )
        data["rss_evaluation"]["results"] = []
        self.assertIn(
            "RSS evaluation must preserve every supplied feed record",
            summarize(discovery, data)["errors"],
        )

    def test_healthy_optional_rss_keeps_blocked_advert_access_informational(
        self,
    ):
        reason = (
            "autowereld.nl: Source redirected to another origin"
            " (myprivacy.dpgmedia.nl); content not validated"
        )
        coverage = {
            "AutoWereld": {
                "source_block_reason": reason,
                "status": "source_unavailable",
                "external_rss_snapshot_status": "fresh_index_only",
                "host_restrictions": {
                    "autowereld.nl": {
                        "category": "external_redirect",
                        "http_status": None,
                    }
                },
            }
        }
        data = evaluate(
            {
                "unverified_rss_leads": [self.lead()],
                "source_coverage": coverage,
            }
        )
        previous = [{"sources": {"AutoWereld": {"zero_bound_streak": 7}}}]
        health = coverage_health(
            data, previous, "new-run", "2026-10-17T14:00:00+00:00"
        )
        row = health["sources"]["AutoWereld"]
        self.assertEqual(row["severity"], "ok")
        self.assertEqual(row["role"], "optional_rss")
        self.assertEqual(row["detail_status"], "blocked")
        self.assertFalse(
            any(a["source"] == "AutoWereld" for a in health["alerts"])
        )
        self.assertEqual(row["failure_kind"], "external_redirect")
        self.assertEqual(row["rss_evaluated"], 1)
        self.assertEqual(row["rss_interesting"], 1)
        self.assertEqual(
            data["rss_evaluation"]["shortlist"][0]["followup_status"],
            "source_access_blocked",
        )
        self.assertIn("Optional RSS tips", render(health))
        self.assertIn("myprivacy.dpgmedia.nl", render(health))
