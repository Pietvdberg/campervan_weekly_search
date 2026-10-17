from copy import deepcopy
from datetime import datetime, timezone
import unittest

from camper_pipeline import screen, evaluate, candidate_state
from research_pack import build
from vehicle_review import assess


class VehicleReviewTests(unittest.TestCase):
    def candidate(self):
        from test_camper_pipeline import ScreeningTests
        return ScreeningTests().example()

    def test_seller_equipment_and_all_five_flags_cannot_replace_independent_checks(self):
        candidate = self.candidate()
        candidate.pop("independent_review")
        result = screen(candidate)
        self.assertEqual(result["score"], 100)
        self.assertFalse(result["qualified"])
        self.assertNotIn("independent cab_ac_working: unverified", result["reasons"])
        self.assertIn("independent available_for_sale: unverified", result["reasons"])

    def test_advertised_ac_is_sufficient_without_claiming_physical_operation(self):
        candidate = self.candidate()
        candidate["independent_review"]["checks"]["cab_ac_working"]["method"] = "advertised_equipment"
        self.assertIsNone(assess(candidate)["checks"]["cab_ac_working"])
        self.assertTrue(screen(candidate)["qualified"])

    def test_expired_future_wrong_vehicle_and_missing_references_remain_unknown(self):
        for change in ({"expires_at": "2001-01-01T00:00:00+00:00"},
                       {"observed_at": "2099-01-01T00:00:00+00:00"},
                       {"plate": "ZZ999Z"}, {"listing_url": "https://example.test/other"}, {"reviewer": ""}):
            candidate = self.candidate()
            candidate["independent_review"].update(change)
            self.assertFalse(screen(candidate)["qualified"])
        candidate = self.candidate()
        candidate["independent_review"]["checks"]["condition_acceptable"].pop("source_url")
        self.assertFalse(screen(candidate)["qualified"])

    def test_failed_independent_condition_is_rejected_without_rdw(self):
        candidate = self.candidate()
        candidate["independent_review"]["checks"]["condition_acceptable"]["confirmed"] = False
        data = evaluate({"candidates": [candidate]}, lambda _: self.fail("Do not spend RDW work on a known failed inspection"))
        self.assertEqual(candidate_state(data["results"][0]), "REJECTED")
        self.assertEqual(data["qualifiers"], 0)

    def test_matching_named_inspection_can_satisfy_review_gates(self):
        self.assertTrue(screen(self.candidate())["qualified"])

    def test_research_pack_is_unfilled_and_does_not_contact_or_verify_anything(self):
        candidate = self.candidate()
        candidate.pop("independent_review")
        result = evaluate({"candidates": [candidate]}, lambda p: {"vehicle": {"status": "ok", "records": [{"kenteken": p}]}})
        pack = build(result)
        self.assertEqual(len(pack["leads"]), 1)
        self.assertEqual(pack["specification_version"], "2.0")
        self.assertIn("bed_width_cm", pack["required_review_measurements"])
        self.assertEqual(pack["review_template"]["requirements"], {})
        assessment = pack["review_template"]["assessments"][0]
        self.assertIsNone(assessment["reviewer"])
        self.assertTrue(all(fact["confirmed"] is None for fact in assessment["checks"].values()))
        self.assertFalse(screen({**candidate, "independent_review": assessment})["qualified"])

    def test_rejected_and_already_qualified_vehicles_do_not_fill_research_queue(self):
        rejected = self.candidate()
        rejected["checks"]["price_incl_vat_within_8000"] = False
        result = evaluate({"candidates": [rejected, self.candidate()]}, lambda p: {"vehicle": {"status": "ok", "records": [{"kenteken": p}]}})
        self.assertEqual(build(result)["leads"], [])

    def test_missing_optional_ac_test_does_not_block_advertised_ac(self):
        candidate = self.candidate()
        candidate["independent_review"]["checks"].pop("cab_ac_working")
        self.assertTrue(screen(candidate)["qualified"])
        candidate["checks"]["cab_ac"] = None
        self.assertFalse(screen(candidate)["qualified"])

    def test_explicit_broken_ac_overrides_equipment_claim(self):
        candidate = self.candidate()
        candidate["independent_review"]["checks"]["cab_ac_working"]["confirmed"] = False
        self.assertEqual(candidate_state(screen(candidate)), "REJECTED")
        candidate = self.candidate()
        candidate["checks"]["cab_ac"] = False
        self.assertEqual(candidate_state(screen(candidate)), "REJECTED")
