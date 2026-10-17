from copy import deepcopy
import unittest

from camper_pipeline import evaluate, screen, candidate_state
from discover_listings import extract
from discovery_queue import select
from search_requirements import evaluate_review, MEASUREMENT_RULES, REVIEW_RULES
from specification_test_fixtures import conversion_fields
import test_camper_pipeline as pipeline_fixtures


class SpecificationV2Tests(unittest.TestCase):
    def test_targets_are_preferences_not_hard_minima(self):
        row = conversion_fields()
        row["measurements"]["available_payload_kg"]["value"] = 100
        result = evaluate_review(row)
        self.assertTrue(result["suitable"])
        self.assertFalse(result["preferences_met"]["finished_standing_height_cm"])
        self.assertFalse(result["preferences_met"]["available_payload_kg"])

    def test_hard_limits_and_mass_consistency(self):
        for key, value in (("bed_length_cm", 169), ("bed_width_cm", 119),
                           ("finished_standing_height_cm", 175), ("external_length_cm", 640),
                           ("maximum_authorised_mass_kg", 3501), ("completed_loaded_mass_kg", 3501),
                           ("completed_loaded_mass_kg", 3200), ("belted_seats", 1)):
            row = conversion_fields()
            row["measurements"][key]["value"] = value
            with self.subTest(key=key):
                self.assertIs(evaluate_review(row)["suitable"], False)

    def test_hard_failure_wins_over_other_missing_measurements(self):
        row = conversion_fields()
        del row["measurements"]["bed_length_cm"]
        row["measurements"]["bed_width_cm"]["value"] = 100
        self.assertIs(evaluate_review(row)["suitable"], False)

    def test_every_measurement_and_layout_check_needs_independent_evidence(self):
        for group, keys in (("measurements", MEASUREMENT_RULES), ("conversion_checks", REVIEW_RULES)):
            for key in keys:
                for change in ({"independently_checked": False}, {"source_url": "http://example.test"}):
                    row = conversion_fields()
                    row[group][key].update(change)
                    self.assertIsNone(evaluate_review(row)["suitable"], (group, key, change))
                row = conversion_fields()
                del row[group][key]
                self.assertIsNone(evaluate_review(row)["suitable"])
        row = conversion_fields()
        row["conversion_checks"]["practical_standing_room"]["confirmed"] = False
        self.assertIs(evaluate_review(row)["suitable"], False)

    def test_old_three_measurement_review_cannot_qualify(self):
        c = pipeline_fixtures.ScreeningTests().example()
        prior = c["conversion_assessment"]
        prior["assessment"]["measurements"] = {key: value for key, value in prior["assessment"]["measurements"].items() if key in prior["requirements"]}
        prior["assessment"].pop("conversion_checks")
        self.assertFalse(screen(c)["qualified"])

    def test_h1_can_qualify_only_after_independent_viable_roof_review(self):
        c = pipeline_fixtures.ScreeningTests().example()
        c["checks"]["high_roof"] = None
        c["checks"]["conversion_suitable"] = None
        row = c["conversion_assessment"]["assessment"]
        data = {"candidates": [c], "conversion_evidence": {"assessments": [row]}}
        result = evaluate(data, lambda plate: {"vehicle": {"status": "ok", "records": [{"kenteken": plate}]}})
        self.assertEqual(result["qualifiers"], 1)
        row = deepcopy(row)
        row["conversion_checks"]["practical_standing_room"]["confirmed"] = False
        data["conversion_evidence"]["assessments"] = [row]
        result = evaluate(data, lambda _: self.fail("Roof failure must not query RDW"))
        self.assertEqual(candidate_state(result["results"][0]), "REJECTED")

    def test_hiace_pop_top_is_discovered_without_fabricating_fit(self):
        url = "https://www.autotrack.nl/a/toyota-hiace-12345678"
        markup = f'<title>Toyota HiAce L1H1 hefdak Airco</title><link rel="canonical" href="{url}"><main>Toyota HiAce L1H1 hefdak Airco</main>'
        candidate = extract("Toyota HiAce", url, "AutoTrack", markup)
        self.assertTrue(candidate["checks"]["high_roof"])
        self.assertIsNone(candidate["checks"]["conversion_suitable"])
        queue, rejected = select([("Toyota HiAce L1H1 hefdak", url)], {}, lambda _: True)
        self.assertEqual(len(queue), 1)
        self.assertEqual(rejected, [])

    def test_invalid_numeric_proof_never_passes(self):
        for value in (True, float("nan"), float("inf"), "3500", -1):
            row = conversion_fields()
            row["measurements"]["maximum_authorised_mass_kg"]["value"] = value
            self.assertIsNone(evaluate_review(row)["suitable"])

    def test_rdw_category_b_conflict_is_rejected_not_a_research_lead(self):
        candidate = pipeline_fixtures.ScreeningTests().example()
        result = evaluate({"candidates": [candidate]}, lambda plate: {"vehicle": {"status": "ok", "records": [{"kenteken": plate, "toegestane_maximum_massa_voertuig": "5000"}]}})
        self.assertEqual(result["qualifiers"], 0)
        self.assertEqual(candidate_state(result["results"][0]), "REJECTED")

    def test_malformed_provenance_is_unknown_instead_of_crashing(self):
        for reference in (123, True, [], {}, "https://[broken", "https://user:password@example.test/report"):
            row = conversion_fields()
            row["measurements"]["bed_width_cm"]["source_url"] = reference
            self.assertIsNone(evaluate_review(row)["suitable"])
