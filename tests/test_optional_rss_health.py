import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from campervan_search.camper_pipeline import evaluate
from campervan_search.search_history import coverage_health
from campervan_search.source_catalog import CORE_SOURCE_NAMES, SOURCE_NAMES
from campervan_search.validate_search import summarize as validation_summary
from campervan_search.verify_discovery import summarize as discovery_summary


class OptionalRssHealthTests(unittest.TestCase):
    def data(self, price=4500):
        coverage = {source: {} for source in SOURCE_NAMES}
        coverage["AutoWereld"] = {
            "external_rss_snapshot_status": "fresh_index_only",
            "source_block_reason": (
                "Source redirected to another origin (myprivacy.dpgmedia.nl);"
                " content not validated"
            ),
            "host_restrictions": {
                "autowereld.nl": {"category": "external_redirect"}
            },
        }
        data = evaluate(
            {
                "source_coverage": coverage,
                "unverified_rss_leads": [
                    {
                        "url": (
                            (
                                "https://www.autowereld.nl/re"
                                "nault/master/l2h2-123/detail"
                                "s.html"
                            )
                        ),
                        "title": "Renault Master L2H2 Airco",
                        "description": "Vraagprijs: € " + str(price),
                    }
                ],
            }
        )
        data["results"] = [
            {
                "candidate": {
                    "source": source,
                    "individual_listing_confirmed": True,
                }
            }
            for source in CORE_SOURCE_NAMES
        ]
        return data

    def health(self, data):
        return coverage_health(
            data,
            [{"sources": {"AutoWereld": {"zero_bound_streak": 99}}}],
            "run",
            "2026-10-17T15:00:00+00:00",
        )

    def test_optional_zero_advert_history_does_not_degrade_healthy_core(self):
        health = self.health(self.data())
        self.assertEqual(health["status"], "bounded_coverage_available")
        self.assertEqual(health["alerts"], [])
        self.assertEqual(health["optional_alerts"], [])
        self.assertEqual(
            health["sources"]["AutoWereld"]["zero_bound_streak"], 100
        )
        self.assertEqual(health["sources"]["AutoWereld"]["severity"], "ok")
        self.assertEqual(health["sources"]["AutoWereld"]["bound"], 0)

    def test_stale_missing_and_invalid_feeds_only_raise_optional_notices(self):
        from campervan_search.coverage_report import main

        for status in ("stale_or_future", "not_supplied", "invalid_json"):
            data = self.data()
            data["source_coverage"]["AutoWereld"][
                "external_rss_snapshot_status"
            ] = status
            health = self.health(data)
            self.assertEqual(health["status"], "bounded_coverage_available")
            self.assertEqual(health["alerts"], [])
            self.assertEqual(
                health["sources"]["AutoWereld"]["severity"], "warning"
            )
            stream = StringIO()
            with (
                patch(
                    "campervan_search.coverage_report.Path.read_text",
                    return_value=json.dumps(health),
                ),
                patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": ""}),
                redirect_stdout(stream),
            ):
                self.assertEqual(main(), 0)
            self.assertIn("::notice::AutoWereld:", stream.getvalue())
            self.assertNotIn("::warning::AutoWereld:", stream.getvalue())
            self.assertNotIn("critical", stream.getvalue())

    def test_no_interesting_results_is_a_valid_completed_feed_assessment(self):
        data = self.data(price=19000)
        health = self.health(data)
        self.assertEqual(data["rss_evaluation"]["counts"]["EXCLUDED"], 1)
        self.assertEqual(health["sources"]["AutoWereld"]["severity"], "ok")
        self.assertEqual(health["sources"]["AutoWereld"]["rss_interesting"], 0)

    def test_incomplete_feed_assessment_is_visible_without_core_degradation(
        self,
    ):
        data = self.data()
        data["rss_evaluation"]["results"] = []
        health = self.health(data)
        self.assertEqual(
            health["sources"]["AutoWereld"]["severity"], "warning"
        )
        self.assertIn("incomplete", health["optional_alerts"][0]["message"])
        self.assertEqual(health["status"], "bounded_coverage_available")

    def test_optional_evidence_cannot_mask_a_complete_core_outage(self):
        data = self.data()
        data["results"] = [
            {
                "candidate": {
                    "source": "AutoWereld",
                    "individual_listing_confirmed": True,
                }
            }
        ]
        self.assertEqual(self.health(data)["status"], "failed")
        self.assertFalse(
            discovery_summary(
                {
                    "candidates": [
                        row["candidate"] for row in data["results"]
                    ],
                    "source_coverage": data["source_coverage"],
                }
            )["development_discovery_verified"]
        )

    def test_missing_optional_metadata_does_not_fail_discovery_or_validation(
        self,
    ):
        candidates = [
            {"source": source, "individual_listing_confirmed": True}
            for source in CORE_SOURCE_NAMES
        ]
        discovery = {
            "candidates": candidates,
            "source_coverage": {source: {} for source in CORE_SOURCE_NAMES},
        }
        summary = discovery_summary(discovery)
        self.assertTrue(summary["development_discovery_verified"])
        self.assertTrue(
            summary["all_core_source_groups_have_bound_candidates"]
        )
        self.assertFalse(summary["all_source_groups_have_bound_candidates"])
        result = evaluate({"source_coverage": discovery["source_coverage"]})
        validated = validation_summary(
            {
                "candidates": [],
                "source_coverage": discovery["source_coverage"],
            },
            result,
        )
        self.assertTrue(validated["validation_passed"], validated["errors"])
