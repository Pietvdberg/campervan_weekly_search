import json
import unittest
from unittest.mock import patch

from campervan_search.discover_listings import extract
from campervan_search.listing_evidence import PLATE, enrich
from campervan_search.listing_identity import bind_evidence
from campervan_search.scoped_state import detail_facts

URL = (
    "https://www.autoscout24.nl/aanbod/peugeot-boxer-9311ec6a"
    "-76fa-47bb-93a2-f49e064f9390"
)


def page(record):
    primary = {
        "@type": "Product",
        "name": "Peugeot Boxer",
        "offers": {"url": URL, "price": 5748, "priceCurrency": "EUR"},
    }
    return (
        '<title>Peugeot Boxer L2H2</title><script type="application/ld+json">'
        + json.dumps(primary)
        + '</script><script id="__NEXT_DATA__">'
        + json.dumps({"props": {"pageProps": {"listingDetails": record}}})
        + "</script>"
    )


def record():
    return {
        "id": "9311ec6a-76fa-47bb-93a2-f49e064f9390",
        "webPage": URL,
        "prices": {
            "public": {
                "price": "€ 5.748",
                "priceRaw": 5748,
                "netPrice": "€ 4.750",
                "netPriceRaw": 4750,
            },
            "suggestedRetail": {"priceRaw": 50000},
        },
        "price": {"isConditionalPrice": False},
        "vehicle": {
            "licensePlate": "02VGK6",
            "modelVersionInput": "L2H2 Airco",
        },
        "location": {
            "zip": "4611AA",
            "street": "Teststraat 12B",
            "countryCode": "NL",
        },
        "status": "Active",
    }


class ScopedStateTests(unittest.TestCase):
    def test_exact_listing_gross_net_fields_restore_vat_price(self):
        scoped, _ = bind_evidence(page(record()), URL)
        result = enrich(
            scoped,
            lambda _: {"code": "Ok", "routes": [{"distance": 25000}]},
            lambda _: {
                "response": {
                    "docs": [
                        {
                            "postcode": "4611AA",
                            "huisnummer": 12,
                            "huisletter": "B",
                            "centroide_ll": "POINT(4.31 51.51)",
                        }
                    ]
                }
            },
        )
        self.assertEqual(result["vat"]["amount_incl_vat"], 5748)
        self.assertEqual(
            result["vat"]["source"], "same_listing_price_specification"
        )
        self.assertEqual(result["distance_km"], 25)
        self.assertEqual(
            result["location_source"], "pdok_verified_full_address"
        )

    def test_other_listing_details_cannot_supply_a_plate_or_price(self):
        other = {**record(), "webPage": URL + "-other"}
        self.assertIsNone(detail_facts(page(other), URL))
        scoped, _ = bind_evidence(page(other), URL)
        self.assertNotIn("02VGK6", scoped)
        self.assertIsNone(enrich(scoped)["vat"]["amount_incl_vat"])

    def test_unknown_net_price_does_not_manufacture_gross_price(
        self,
    ):
        for change in (
            {"price": {"isConditionalPrice": True}},
            {"prices": {"public": {"price": "€ 5748", "priceRaw": 5748}}},
        ):
            facts = detail_facts(page({**record(), **change}), URL)
            self.assertNotIn("priceSpecification", facts)

    def test_unhyphenated_label_and_structured_plate_are_supported(self):
        self.assertEqual(PLATE.findall("Kenteken V09RJG"), ["V09RJG"])
        with patch(
            "campervan_search.discover_listings.enrich",
            return_value={
                "vat": {"amount_incl_vat": None, "basis": "unknown"},
                "checks": {},
                "distance_km": None,
                "location_coordinates": None,
            },
        ):
            candidate = extract("Boxer", URL, "AutoScout24", page(record()))
        self.assertEqual(candidate["plate"], "02VGK6")
        self.assertTrue(candidate["plate_confirmed_from_listing"])
        self.assertTrue(candidate["checks"]["high_roof"])
        self.assertTrue(candidate["checks"]["cab_ac"])
        self.assertNotIn("cab_ac_working", candidate)

    def test_conflicting_same_page_plates_stay_unconfirmed(self):
        content = (
            page(record())
            + '<link rel="canonical" href="'
            + URL
            + '"><main>Kenteken ZZ999Z</main>'
        )
        with patch(
            "campervan_search.discover_listings.enrich",
            return_value={
                "vat": {"amount_incl_vat": None, "basis": "unknown"},
                "checks": {},
                "distance_km": None,
                "location_coordinates": None,
            },
        ):
            candidate = extract("Boxer", URL, "AutoScout24", content)
        self.assertFalse(candidate["plate_confirmed_from_listing"])
        self.assertEqual(
            set(candidate["plate_conflicts"]), {"02VGK6", "ZZ999Z"}
        )

    def test_unsupported_marketplace_cannot_claim_known_state_semantics(self):
        self.assertIsNone(
            detail_facts(
                page(record()), URL.replace("autoscout24.nl", "other.test")
            )
        )

    def test_autotrack_syndication_requires_exact_uuid_and_its_page_controller(
        self,
    ):
        track_url = URL.replace("autoscout24.nl/aanbod/", "autotrack.nl/a/")
        state = {
            "listingDetails": record(),
            "canonicalOrigin": "https://www.autotrack.nl",
            "marketplace": {"domain": "autotrack_nl"},
        }
        content = (
            '<script id="__NEXT_DATA__">' + json.dumps(state) + "</script>"
        )
        self.assertIsNotNone(detail_facts(content, track_url))
        for change in (
            {"canonicalOrigin": "https://other.test"},
            {"marketplace": {"domain": "other"}},
            {
                "listingDetails": {
                    **record(),
                    "id": "00000000-0000-0000-0000-000000000000",
                }
            },
        ):
            invalid = (
                '<script id="__NEXT_DATA__">'
                + json.dumps({**state, **change})
                + "</script>"
            )
            self.assertIsNone(detail_facts(invalid, track_url))
