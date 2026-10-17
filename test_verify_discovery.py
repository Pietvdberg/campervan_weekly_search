import unittest
from source_catalog import SOURCE_NAMES
from verify_discovery import summarize


class DiscoveryAcceptanceTests(unittest.TestCase):
    def test_unbound_page_cannot_pass_development_acceptance(self):
        result = summarize({"source_coverage": {name: {} for name in SOURCE_NAMES},
                            "candidates": [{"source": "Marktplaats", "individual_listing_confirmed": False}]})
        self.assertFalse(result["development_discovery_verified"])

    def test_partial_discovery_is_not_complete_or_production_ready(self):
        result = summarize({"source_coverage": {name: {} for name in SOURCE_NAMES},
                            "candidates": [{"source": "Marktplaats", "individual_listing_confirmed": True}]})
        self.assertTrue(result["development_discovery_verified"])
        self.assertFalse(result["all_source_groups_have_bound_candidates"])
        self.assertFalse(result["production_ready"])
        self.assertEqual(len(result["sources_without_identity_bound_candidates"]), 5)

    def test_missing_coverage_cannot_pass_even_with_bound_candidate(self):
        result = summarize({"candidates": [{"source": "Marktplaats", "individual_listing_confirmed": True}]})
        self.assertFalse(result["development_discovery_verified"])
