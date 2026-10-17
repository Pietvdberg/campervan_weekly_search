import io
import json
import unittest
from unittest.mock import patch

from campervan_search.discover_listings import extract, fetch
from campervan_search.listing_identity import (
    bind_evidence,
    require_same_listing,
)

URL = "https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123456-boxer"


class IdentityTests(unittest.TestCase):
    def candidate(self, markup):
        return extract("Peugeot Boxer L2H2 Airco", URL, "Marktplaats", markup)

    def test_unbound_page_cannot_supply_plate_or_equipment(self):
        candidate = self.candidate(
            "<title>Boxer</title><p>Boxer L2H2 airco Kenteken: AB-123-C € 6000"
            " incl btw</p>"
        )
        self.assertFalse(candidate["individual_listing_confirmed"])
        self.assertIsNone(candidate["plate"])
        self.assertTrue(
            all(value is None for value in candidate["checks"].values())
        )

    def test_related_cards_cannot_supply_plate_price_or_equipment(self):
        page = (
            f'<link rel="canonical" href="{URL}"><main>Peugeot Boxer<p>€ 9000'
            " incl btw</p><aside>Boxer L2H2 airco Kenteken: AB-123-C € 5000"
            " incl btw</aside></main>"
        )
        candidate = self.candidate(page)
        self.assertIsNone(candidate["plate"])
        self.assertIsNone(candidate["checks"]["cab_ac"])
        self.assertEqual(candidate["price_incl_vat"], 9000)

    def test_canonical_mismatch_rejects_listing(self):
        self.assertIsNone(
            self.candidate(
                '<link rel="canonical" href="/l/auto-s"><main>Peugeot Boxer'
                " airco</main>"
            )
        )

    def test_matching_primary_excludes_other_vehicle_offers_and_coordinates(
        self,
    ):
        nodes = [
            {
                "@type": "Car",
                "url": URL + "-other",
                "name": "Boxer L2H2 airco",
                "offers": {"price": "5000", "priceCurrency": "EUR"},
                "geo": {"latitude": 51.5, "longitude": 4.3},
            },
            {
                "@type": "Car",
                "url": URL,
                "name": "Peugeot Boxer",
                "offers": {"price": "9500", "priceCurrency": "EUR"},
            },
        ]
        candidate = self.candidate(
            '<title>Boxer</title><script type="application/ld+json">'
            + json.dumps(nodes)
            + "</script>"
        )
        self.assertTrue(candidate["individual_listing_confirmed"])
        self.assertIsNone(candidate["location_coordinates"])
        self.assertIsNone(candidate["checks"]["cab_ac"])
        self.assertIsNone(candidate["price_incl_vat"])

    def test_conflicting_primary_objects_rejected(self):
        nodes = [
            {"@type": "Car", "url": URL, "name": "Boxer A"},
            {"@type": "Car", "url": URL, "name": "Boxer B"},
        ]
        self.assertIsNone(
            self.candidate(
                '<title>Boxer</title><script type="application/ld+json">'
                + json.dumps(nodes)
                + "</script>"
            )
        )

    def test_other_vehicle_object_does_not_bind_to_requested_url(self):
        page = (
            '<title>Boxer</title><script type="application/ld+json">'
            + json.dumps(
                {"@type": "Car", "url": URL + "-other", "name": "Boxer airco"}
            )
            + "</script>"
        )
        self.assertFalse(self.candidate(page)["individual_listing_confirmed"])

    def test_tracking_and_www_variants_preserve_identity(self):
        require_same_listing(URL, URL.replace("www.", "") + "?tracking=1")

    def test_redirect_to_inventory_or_other_advert_rejected(self):
        for target in (
            "https://www.marktplaats.nl/l/auto-s",
            URL + "-other",
            "https://other.test" + URL.split(".nl")[1],
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                require_same_listing(URL, target)

    def test_http_fetch_checks_final_url(self):
        response = io.BytesIO(b"<main>Boxer</main>")
        response.geturl = lambda: "https://www.marktplaats.nl/l/auto-s"
        response.headers = {"Content-Type": "text/html"}
        with (
            patch(
                "campervan_search.discover_listings.urlopen",
                return_value=response,
            ),
            self.assertRaises(ValueError),
        ):
            fetch(URL)

    def test_multiple_main_regions_do_not_bind_visible_fields(self):
        markup = (
            '<link rel="canonical"'
            f' href="{URL}"><main>Boxer</main><main>airco</main>'
        )
        self.assertEqual(bind_evidence(markup, URL)[1]["status"], "unbound")

    def test_primary_offer_url_binds_vehicle_without_root_url(self):
        for kind in ("Vehicle", "Product"):
            node = {
                "@type": kind,
                "name": "Peugeot Boxer L2H2 airco",
                "offers": {
                    "@type": "Offer",
                    "url": URL,
                    "price": 7000,
                    "priceCurrency": "EUR",
                },
            }
            page = (
                "<title>Peugeot Boxer</title><script"
                ' type="application/ld+json">' + json.dumps(node) + "</script>"
            )
            candidate = self.candidate(page)
            self.assertTrue(candidate["individual_listing_confirmed"])
            self.assertTrue(candidate["checks"]["high_roof"])
            self.assertTrue(candidate["checks"]["cab_ac"])
            self.assertIsNone(candidate["price_incl_vat"])

    def test_mismatched_offer_cannot_override_primary_identity(self):
        node = {
            "@type": "Vehicle",
            "url": URL + "-other",
            "name": "Boxer",
            "offers": {"url": URL},
        }
        page = (
            '<title>Peugeot Boxer</title><script type="application/ld+json">'
            + json.dumps(node)
            + "</script>"
        )
        self.assertFalse(self.candidate(page)["individual_listing_confirmed"])

    def test_offer_binding_keeps_nested_car_and_seller_address(self):
        node = {
            "@type": "Product",
            "name": "Boxer",
            "offers": {
                "url": URL,
                "itemOffered": {"@type": "Car", "name": "Peugeot Boxer"},
                "offeredBy": {
                    "@type": "AutoDealer",
                    "address": {
                        "postalCode": "1234 AB",
                        "streetAddress": "Teststraat 7b",
                    },
                },
            },
        }
        scoped, provenance = bind_evidence(
            '<script type="application/ld+json">'
            + json.dumps(node)
            + "</script>",
            URL,
        )
        self.assertEqual(provenance["status"], "bound")
        self.assertIn("postalCode", scoped)
        self.assertIn("Teststraat 7b", scoped)

    def test_configured_inventory_redirect_may_change_path_but_not_host(self):
        require_same_listing(
            "https://www.example.test/inventory",
            "https://example.test/new-inventory",
            inventory=True,
        )
        for target in (
            "https://other.test/inventory",
            "http://www.example.test/inventory",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                require_same_listing(
                    "https://www.example.test/inventory",
                    target,
                    inventory=True,
                )

    def test_detail_seed_keeps_strict_identity(self):
        from campervan_search.source_catalog import INVENTORY_SEEDS, SEED_PAGES

        self.assertNotIn(SEED_PAGES["AutoWereld"][0], INVENTORY_SEEDS)
        self.assertIn(SEED_PAGES["Local dealers"][0], INVENTORY_SEEDS)

    def test_fetch_allows_same_host_inventory_redirect(self):
        from campervan_search.source_catalog import SEED_PAGES

        requested = SEED_PAGES["Local dealers"][0]
        response = io.BytesIO(b"<main>Inventory</main>")
        response.geturl = lambda: (
            "https://www.autowereld.nl/aanbieder/current-"
            "inventory/auto.html"
        )
        response.headers = {"Content-Type": "text/html"}
        with patch(
            "campervan_search.discover_listings.urlopen", return_value=response
        ):
            markup, kind = fetch(requested)
        self.assertIn("Inventory", markup)
        self.assertEqual(kind, "text/html")
