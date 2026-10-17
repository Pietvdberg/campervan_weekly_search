from copy import deepcopy
from datetime import datetime, timezone
import unittest

from camper_pipeline import evaluate
from conversion_evidence import assess
import test_camper_pipeline as pipeline_fixtures


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.candidate = pipeline_fixtures.ScreeningTests().example()
        self.candidate["checks"]["conversion_suitable"] = None
        # Fictional test minima and measurements, not user requirements.
        self.requirements = {"available_payload_kg": 500, "internal_height_cm": 180, "internal_length_cm": 300}
        self.row = {"plate": "AB123C", "listing_url": self.candidate["listing_url"],
                    "reviewer": "Synthetic test reviewer", "observed_at": "2026-10-16T00:00:00+00:00",
                    "expires_at": "2026-10-18T00:00:00+00:00",
                    "measurements": {key: {"value": value, "source_url": "https://example.test/measurement", "independently_checked": True} for key, value in self.requirements.items()}}
        from specification_test_fixtures import add_conversion_fields
        add_conversion_fields(self.row)
        self.now = datetime(2026, 10, 17, tzinfo=timezone.utc)

    def result(self, row=None, requirements=None):
        return assess(self.candidate, self.requirements if requirements is None else requirements,
                      [self.row if row is None else row], now=self.now)

    def test_exact_minima_pass(self):
        self.assertTrue(self.result()["suitable"])

    def test_specification_supplies_hard_rules_without_custom_minima(self):
        self.assertTrue(self.result(requirements={})["suitable"])

    def test_failed_payload_rejects(self):
        row = deepcopy(self.row)
        row["measurements"]["available_payload_kg"]["value"] -= 1
        self.assertIs(self.result(row)["suitable"], False)

    def test_wrong_vehicle_stale_or_unreviewed_measurements_stay_unknown(self):
        for field, value in (("plate", "ZZ999Z"), ("listing_url", "https://example.test/other"),
                             ("reviewer", ""), ("expires_at", "2026-10-16T00:00:00+00:00"),
                             ("observed_at", "2026-10-18T00:00:00+00:00")):
            row = {**self.row, field: value}
            with self.subTest(field=field):
                self.assertIsNone(self.result(row)["suitable"])
        for value in (False, None, "yes"):
            row = deepcopy(self.row)
            row["measurements"]["available_payload_kg"]["independently_checked"] = value
            self.assertIsNone(self.result(row)["suitable"])

    def test_invalid_numeric_measurements_cannot_pass(self):
        for value in (True, float("nan"), float("inf"), -1, "500"):
            row = deepcopy(self.row)
            row["measurements"]["available_payload_kg"]["value"] = value
            with self.subTest(value=value):
                self.assertIsNone(self.result(row)["suitable"])

    def test_conflicting_reviews_remain_unknown(self):
        self.assertIsNone(assess(self.candidate, self.requirements, [self.row, self.row], self.now)["suitable"])

    def test_end_to_end_reviewed_candidate_can_qualify(self):
        # Keep this fixture independent of wall-clock date.
        row = {**self.row, "observed_at": "2000-01-01T00:00:00+00:00", "expires_at": "2100-01-01T00:00:00+00:00"}
        data = {"candidates": [self.candidate], "conversion_evidence": {"requirements": self.requirements, "assessments": [row]}}
        result = evaluate(data, lambda plate: {"vehicle": {"status": "ok", "records": [{"kenteken": plate}]}})
        self.assertEqual(result["qualifiers"], 1)
        self.assertEqual(result["results"][0]["candidate"]["conversion_assessment"]["assessment"]["reviewer"], row["reviewer"])
        self.assertIsNone(self.candidate["checks"]["conversion_suitable"])

    def test_failed_review_prevents_rdw_and_qualification(self):
        row = deepcopy(self.row)
        row.update(observed_at="2000-01-01T00:00:00+00:00", expires_at="2100-01-01T00:00:00+00:00")
        row["measurements"]["internal_height_cm"]["value"] = 100
        result = evaluate({"candidates": [self.candidate], "conversion_evidence": {"requirements": self.requirements, "assessments": [row]}}, lambda _: self.fail("Rejected candidate must not trigger RDW"))
        self.assertEqual(result["qualifiers"], 0)
