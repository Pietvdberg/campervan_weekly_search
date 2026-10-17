import unittest
from unittest.mock import patch
from discover_listings import extract
from camper_pipeline import evaluate


class ReviewRegressions(unittest.TestCase):
    def test_denied_or_broken_features_never_pass(self):
        for text, key, expected in [
            ("Peugeot Boxer L2H2 zonder airco", "cab_ac", False),
            ("Peugeot Boxer L2H2 geen airconditioning", "cab_ac", False),
            ("Peugeot Boxer L2H2 airco werkt niet", "cab_ac", False),
            ("Peugeot Boxer L2H2 airco: nee", "cab_ac", False),
            ("Peugeot Boxer L2H2 airco defect", "cab_ac", False),
            ("Peugeot Boxer zonder hoog dak", "high_roof", False),
            ("Peugeot Boxer L2H2 airco aanwezig. Zonder airco geleverd", "cab_ac", None),
            ("Peugeot Boxer L2H2 airco", "cab_ac", True),
        ]:
            with self.subTest(text=text), patch("discover_listings.enrich", return_value={"checks": {}, "vat": {"amount_incl_vat": None, "basis": "unknown"}, "distance_km": None, "location_coordinates": None}):
                item = extract("Boxer L2H2 airco", "https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123456", "Marktplaats", '<link rel="canonical" href="https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123456"><main>' + text + "</main>")
            self.assertIs(item["checks"][key], expected)

    def test_wrong_rdw_registration_cannot_qualify(self):
        from test_camper_pipeline import ScreeningTests
        result = evaluate({"candidates": [ScreeningTests().example()]}, lambda p: {"vehicle": {"status": "ok", "records": [{"kenteken": "ZZ999Z"}]}})
        self.assertEqual(result["qualifiers"], 0)

    def test_failed_apk_or_catalogue_prevents_qualification(self):
        from test_camper_pipeline import ScreeningTests
        for extra in ({"status": "error"}, {"defects": {"status": "error"}},
                      {"defect_catalogue_errors": [{"code": "123", "error": "HTTP 503"}]}):
            result = evaluate({"candidates": [ScreeningTests().example()]}, lambda plate: {
                "vehicle": {"status": "ok", "records": [{"kenteken": plate}]}, **extra})
            self.assertEqual(result["qualifiers"], 0)
            self.assertIn("RDW/APK lookup incomplete", result["results"][0]["reasons"])

    def test_viabovag_plain_plate_fallback(self):
        from discover_listings import is_vehicle_detail
        url = "https://www.viabovag.nl/auto/aanbod/peugeot-boxer-123abc"
        self.assertTrue(is_vehicle_detail(url, "viaBOVAG", "<p>Kenteken: AB-123-C</p>"))

    def test_primary_low_roof_title_overrides_unrelated_high_roof_mentions(self):
        from discover_listings import extract
        url = "https://www.autotrack.nl/a/peugeot-boxer-diesel-2019-58405822"
        page = f'<title>Peugeot Boxer L1H1</title><link rel="canonical" href="{url}"><main>Peugeot Boxer L1H1 Airco. Other L2H2 vans also available.</main>'
        candidate = extract("Peugeot Boxer L2H2", url, "AutoTrack", page)
        self.assertIs(candidate["checks"]["high_roof"], False)
