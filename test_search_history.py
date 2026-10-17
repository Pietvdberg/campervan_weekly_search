from copy import deepcopy
import unittest
from search_history import empty_state, update, coverage_health
from camper_pipeline import evaluate, report_selection
from source_catalog import SOURCE_NAMES


class HistoryTests(unittest.TestCase):
    def data(self, price=6000, plate="AB123C", url="https://example.test/van"):
        candidate = {"name":"Synthetic van", "source":"AutoScout24", "listing_url":url,
                     "individual_listing_confirmed":True,"plate":plate,"plate_confirmed_from_listing":bool(plate),
                     "price_incl_vat":price,"distance_km":20,"checks":{"high_roof":True,"cab_ac":True,"distance_within_100km":True,"price_incl_vat_within_8000":True,"conversion_suitable":None}}
        return evaluate({"candidates":[candidate],"source_coverage":{s:{} for s in SOURCE_NAMES}}, lambda p:{"vehicle":{"status":"ok","records":[{"kenteken":p}]}})

    def test_new_unchanged_drop_relist_and_rerun(self):
        first, state = update(self.data(), empty_state(), "1", "2026-10-01T00:00:00+00:00")
        self.assertEqual(first["results"][0]["history"]["status"], "newly_observed")
        second, state = update(self.data(), state, "2", "2026-10-08T00:00:00+00:00")
        self.assertEqual(second["results"][0]["history"]["status"], "unchanged")
        self.assertEqual(report_selection(second)["potential"], [])
        dropped, state = update(self.data(5500), state, "3", "2026-10-15T00:00:00+00:00")
        self.assertEqual(dropped["results"][0]["history"]["status"], "material_price_drop")
        rerun, same = update(self.data(5400), state, "3", "2026-10-15T12:00:00+00:00")
        self.assertEqual(same, state)
        self.assertTrue(rerun["history_summary"]["rerun"])
        relisted, state = update(self.data(5500,url="https://other.test/listing"), state, "4", "2026-10-16T00:00:00+00:00")
        self.assertEqual(relisted["results"][0]["history"]["status"], "relisted_or_new_source")
        self.assertFalse(relisted["results"][0]["history"]["show_in_digest"])
        self.assertEqual(len(state["listings"]), 1)

    def test_tracking_url_plate_promotion_and_source_conflicts_preserve_history(self):
        _, state = update(self.data(plate=None,url="https://example.test/van?tracking=1"), empty_state(), "1", "2026-10-01T00:00:00+00:00")
        data = self.data(url="https://www.example.test/van")
        _, state = update(data, state, "2", "2026-10-02T00:00:00+00:00")
        self.assertEqual(len(state["listings"]), 1)
        self.assertEqual(next(iter(state["listings"].values()))["first_seen"], "2026-10-01T00:00:00+00:00")
        data["results"] += deepcopy(self.data(6500,url="https://other.test/van")["results"])
        result, state = update(data, state, "3", "2026-10-03T00:00:00+00:00")
        self.assertEqual(result["results"][0]["history"]["conflicting_source_prices"], [6000,6500])
        self.assertEqual(len(next(iter(state["listings"].values()))["observations"]), 2)

    def test_price_tweak_and_disappearance_do_not_invent_market_events(self):
        _, state = update(self.data(), empty_state(), "1")
        result, state = update(self.data(5900), state, "2")
        self.assertEqual(result["results"][0]["history"]["status"], "unchanged")
        result, state = update({"results":[],"source_coverage":{}}, state, "3")
        self.assertEqual(len(state["listings"]), 1)
        self.assertEqual(result["coverage_health"]["status"], "failed")

    def test_coverage_regression_and_repeat_failure_remain_visible(self):
        _, state = update(self.data(), empty_state(), "1")
        empty = {"results":[],"source_coverage":{s:{} for s in SOURCE_NAMES}}
        result, state = update(empty, state, "2")
        self.assertEqual(result["coverage_health"]["sources"]["AutoScout24"]["severity"], "critical")
        result, state = update(empty, state, "3")
        self.assertEqual(result["coverage_health"]["sources"]["AutoWereld"]["zero_bound_streak"], 3)
        self.assertFalse(result["coverage_health"]["exhaustive"])

    def test_corrupt_state_is_not_silently_reset(self):
        with self.assertRaises(ValueError):
            update(self.data(), {"schema_version":99}, "1")

    def test_conflicting_confirmed_registration_keeps_both_records_and_blocks_matches(self):
        _, state = update(self.data(), empty_state(), "1")
        result, state = update(self.data(plate="ZZ999Z"), state, "2")
        self.assertEqual(len(state["listings"]), 2)
        self.assertFalse(result["results"][0]["search_assessment"]["matched"])
        result, state = update(self.data(plate="ZZ999Z"), state, "3")
        self.assertFalse(result["results"][0]["search_assessment"]["matched"])

    def test_changed_sample_cap_does_not_invent_count_regression(self):
        data = self.data()
        data["results"] *= 8
        data["run_metadata"] = {"max_per_source": 50}
        _, state = update(data, empty_state(), "1")
        data = self.data()
        data["run_metadata"] = {"max_per_source": 8}
        result, _ = update(data, state, "2")
        self.assertEqual(result["coverage_health"]["sources"]["AutoScout24"]["severity"], "ok")

    def test_external_evidence_loss_is_not_a_seller_advert_change(self):
        _, state = update(self.data(), empty_state(), "1")
        data = self.data()
        data["results"][0]["candidate"]["checks"]["distance_within_100km"] = None
        result, _ = update(data, state, "2")
        self.assertEqual(result["results"][0]["history"]["status"], "evidence_updated")
