import io
import json
import unittest
from unittest.mock import patch

from discover_listings import extract, fetch
from listing_identity import bind_evidence, require_same_listing

URL = "https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123456-boxer"


class IdentityTests(unittest.TestCase):
    def candidate(self, markup):
        return extract("Peugeot Boxer L2H2 Airco", URL, "Marktplaats", markup)

    def test_unbound_page_cannot_supply_plate_or_equipment(self):
        candidate = self.candidate("<title>Boxer</title><p>Boxer L2H2 airco Kenteken: AB-123-C € 6000 incl btw</p>")
        self.assertFalse(candidate["individual_listing_confirmed"])
        self.assertIsNone(candidate["plate"])
        self.assertTrue(all(value is None for value in candidate["checks"].values()))

    def test_related_cards_cannot_supply_plate_price_or_equipment(self):
        page = f'<link rel="canonical" href="{URL}"><main>Peugeot Boxer<p>€ 9000 incl btw</p><aside>Boxer L2H2 airco Kenteken: AB-123-C € 5000 incl btw</aside></main>'
        candidate = self.candidate(page)
        self.assertIsNone(candidate["plate"])
        self.assertIsNone(candidate["checks"]["cab_ac"])
        self.assertEqual(candidate["price_incl_vat"], 9000)

    def test_canonical_mismatch_rejects_listing(self):
        self.assertIsNone(self.candidate('<link rel="canonical" href="/l/auto-s"><main>Peugeot Boxer airco</main>'))

    def test_matching_primary_excludes_other_vehicle_offers_and_coordinates(self):
        nodes = [
            {"@type": "Car", "url": URL + "-other", "name": "Boxer L2H2 airco", "offers": {"price": "5000", "priceCurrency": "EUR"}, "geo": {"latitude": 51.5, "longitude": 4.3}},
            {"@type": "Car", "url": URL, "name": "Peugeot Boxer", "offers": {"price": "9500", "priceCurrency": "EUR"}},
        ]
        candidate = self.candidate('<title>Boxer</title><script type="application/ld+json">' + json.dumps(nodes) + '</script>')
        self.assertTrue(candidate["individual_listing_confirmed"])
        self.assertIsNone(candidate["location_coordinates"])
        self.assertIsNone(candidate["checks"]["cab_ac"])
        self.assertIsNone(candidate["price_incl_vat"])

    def test_conflicting_primary_objects_rejected(self):
        nodes = [{"@type": "Car", "url": URL, "name": "Boxer A"}, {"@type": "Car", "url": URL, "name": "Boxer B"}]
        self.assertIsNone(self.candidate('<title>Boxer</title><script type="application/ld+json">' + json.dumps(nodes) + '</script>'))

    def test_other_vehicle_object_does_not_bind_to_requested_url(self):
        page = '<title>Boxer</title><script type="application/ld+json">' + json.dumps({"@type": "Car", "url": URL + "-other", "name": "Boxer airco"}) + '</script>'
        self.assertFalse(self.candidate(page)["individual_listing_confirmed"])

    def test_tracking_and_www_variants_preserve_identity(self):
        require_same_listing(URL, URL.replace("www.", "") + "?tracking=1")

    def test_redirect_to_inventory_or_other_advert_rejected(self):
        for target in ("https://www.marktplaats.nl/l/auto-s", URL + "-other", "https://other.test" + URL.split(".nl")[1]):
            with self.subTest(target=target), self.assertRaises(ValueError):
                require_same_listing(URL, target)

    def test_http_fetch_checks_final_url(self):
        response = io.BytesIO(b"<main>Boxer</main>")
        response.geturl = lambda: "https://www.marktplaats.nl/l/auto-s"
        response.headers = {"Content-Type": "text/html"}
        with patch("discover_listings.urlopen", return_value=response), self.assertRaises(ValueError):
            fetch(URL)

    def test_multiple_main_regions_do_not_bind_visible_fields(self):
        markup = f'<link rel="canonical" href="{URL}"><main>Boxer</main><main>airco</main>'
        self.assertEqual(bind_evidence(markup, URL)[1]["status"], "unbound")
