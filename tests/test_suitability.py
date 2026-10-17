import unittest
from datetime import date

from campervan_search.suitability import WEIGHTS, rank, variant_research


class SuitabilityTests(unittest.TestCase):
    def item(self):
        return {
            "candidate": {
                "listing_url": "https://example.test/van",
                "price_incl_vat": 5000,
                "variant": {
                    "make": "Peugeot",
                    "model": "Boxer",
                    "generation": "II 2006-2014",
                    "engine": "2.2 HDi",
                    "gearbox": "6-speed manual",
                    "body": "L2H2",
                },
            },
            "search_assessment": {"matched": True, "status": "SEARCH_MATCH"},
        }

    def test_specification_weights_and_unknowns_are_explicit(self):
        self.assertEqual(len(WEIGHTS), 32)
        self.assertEqual(WEIGHTS["reliability"], 10)
        self.assertEqual(WEIGHTS["storage"], 7.5)
        result = rank(self.item())
        self.assertEqual(result["category"], "C")
        self.assertFalse(result["critical_research_supported"])
        self.assertLess(result["weighted_coverage_percent"], 5)
        self.assertIn("reliability", result["unknown_criteria"])

    def test_sourced_scores_rank_only_after_hard_filters(self):
        item = self.item()
        item["candidate"]["suitability_evidence"] = {
            key: {
                "score": 9,
                "source_url": "https://example.test/assessment",
                "reason": "Fictional review of this exact variant",
                "confidence": "high",
            }
            for key in WEIGHTS
        }
        self.assertEqual(rank(item)["category"], "A")
        item["search_assessment"] = {"matched": False, "status": "REJECTED"}
        self.assertEqual(rank(item)["category"], "D")
        item["candidate"]["variant"].pop("gearbox")
        self.assertFalse(rank(item)["critical_research_supported"])

    def test_invalid_unattributed_or_low_confidence_scores_are_not_used(self):
        for change in (
            {"score": True},
            {"score": 11},
            {"score": float("nan")},
            {"source_url": "http://example.test"},
            {"confidence": "low"},
            {"reason": ""},
        ):
            item = self.item()
            fact = {
                "score": 9,
                "source_url": "https://example.test/review",
                "reason": "Reason",
                "confidence": "high",
                **change,
            }
            item["candidate"]["suitability_evidence"] = {"reliability": fact}
            self.assertNotIn("reliability", rank(item)["criteria"])

    def test_registry_never_borrows_another_engine_and_expires(self):
        c = self.item()["candidate"]
        result = variant_research(c, today=date(2026, 10, 17))
        self.assertTrue(result["notes"])
        c["variant"]["engine"] = "3.0 HDi"
        result = variant_research(c, today=date(2026, 10, 17))
        self.assertEqual(
            [r["id"] for r in result["notes"]], ["boxer-3-hdi-timing"]
        )
        self.assertFalse(variant_research(c, today=date(2030, 1, 1))["notes"])

    def test_inferred_generation_is_labeled_not_exact(self):
        c = {
            "variant_clues": [
                {
                    "make": "Peugeot",
                    "model": "Boxer",
                    "productionYear": 2010,
                    "modelVersionInput": "2.2 HDi L2H2",
                    "transmissionType": "Manual",
                    "gears": 6,
                }
            ]
        }
        result = variant_research(c, today=date(2026, 10, 17))
        self.assertFalse(result["exact_variant_identified"])
        self.assertEqual(result["inferred_identity_fields"], ["generation"])
        self.assertTrue(result["notes"])
