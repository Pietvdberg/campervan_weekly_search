import unittest
from copy import deepcopy

from campervan_search.camper_pipeline import evaluate, screen
from campervan_search.source_catalog import SOURCE_NAMES
from campervan_search.validate_search import compare, summarize


class SearchValidationTests(unittest.TestCase):
    def data(self):
        from tests.test_camper_pipeline import ScreeningTests

        candidate = ScreeningTests().example()
        candidate.update(
            source="Marktplaats", price_incl_vat=7000, distance_km=25
        )
        discovery = {
            "candidates": [candidate],
            "source_coverage": {source: {} for source in SOURCE_NAMES},
        }
        result = evaluate(
            discovery,
            lambda plate: {
                "status": "ok",
                "vehicle": {"status": "ok", "records": [{"kenteken": plate}]},
                "defects": {"status": "ok", "records": []},
            },
        )
        return discovery, result

    def test_valid_end_to_end_fixture_and_legitimate_zero_matches(self):
        discovery, result = self.data()
        self.assertEqual(result["qualifiers"], 1)
        validation = summarize(discovery, result)
        self.assertTrue(validation["validation_passed"])
        self.assertFalse(validation["production_ready"])
        zero = {"results": [], "qualifiers": 0}
        empty = {
            "candidates": [],
            "source_coverage": {source: {} for source in SOURCE_NAMES},
        }
        self.assertTrue(summarize(empty, zero)["validation_passed"])
        self.assertEqual(
            summarize(empty, zero)["stages"]["discovery"], "partial"
        )

    def test_impossible_budget_or_route_pass_fails_validation(self):
        for field, bad_value in (
            ("price_incl_vat", None),
            ("price_incl_vat", 9000),
            ("distance_km", 130),
        ):
            discovery, result = self.data()
            result["results"][0]["candidate"][field] = bad_value
            validation = summarize(discovery, result)
            self.assertFalse(validation["validation_passed"])

    def test_missing_physical_proof_cannot_be_qualified_by_boolean_flags(self):
        discovery, result = self.data()
        result["results"][0]["candidate"].pop("independent_review")
        self.assertFalse(summarize(discovery, result)["validation_passed"])
        candidate = self.data()[0]["candidates"][0]
        candidate.pop("conversion_assessment")
        self.assertFalse(screen(candidate)["qualified"])

    def test_wrong_registration_and_missing_discovery_record_are_detected(
        self,
    ):
        discovery, result = self.data()
        result["results"][0]["rdw"]["vehicle"]["records"][0][
            "kenteken"
        ] = "ZZ999Z"
        self.assertFalse(summarize(discovery, result)["validation_passed"])
        discovery["candidates"] = []
        self.assertTrue(
            any(
                "identities/counts" in reason
                for reason in summarize(discovery, result)["errors"]
            )
        )

    def test_comparison_pairs_identical_source_and_url_not_unrelated_records(
        self,
    ):
        _, after = self.data()
        before = deepcopy(after)
        before["results"][0]["candidate"]["price_incl_vat"] = None
        comparison = compare(before, after)
        self.assertEqual(
            comparison["matched_record_evidence_gains"][
                "price_incl_vat_unknown_to_known"
            ],
            1,
        )
        before["results"][0]["candidate"]["listing_url"] += "-different"
        comparison = compare(before, after)
        self.assertEqual(comparison["common_source_listing_records"], 0)
        self.assertEqual(
            comparison["matched_record_evidence_gains"][
                "price_incl_vat_unknown_to_known"
            ],
            0,
        )
