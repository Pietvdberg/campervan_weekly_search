from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from camper_pipeline import evaluate
from discover_listings import extract
from listing_evidence import enrich
from report_html import render_html
from source_catalog import SOURCE_NAMES
from validate_search import summarize

URL = "https://www.autoscout24.nl/aanbod/peugeot-boxer-9311ec6a-76fa-47bb-93a2-f49e064f9390"


class EndToEndEvidenceTests(unittest.TestCase):
    def exercise(self, alteration=None):
        # Sanitized realistic marketplace shape; all observations/criteria are fictional.
        primary = {"@type": "Product", "name": "Peugeot Boxer L2H2", "offers": {"url": URL, "price": 5748, "priceCurrency": "EUR"}}
        state = {"listingDetails": {"webPage": URL, "id": URL.rsplit("-", 1)[-1],
            "prices": {"public": {"price": "€ 5748", "priceRaw": 5748, "netPrice": "€ 4750", "netPriceRaw": 4750}},
            "price": {"isConditionalPrice": False}, "vehicle": {"licensePlate": "AB123C", "modelVersionInput": "L2H2 Airco"},
            "location": {"zip": "4611AA", "street": "Teststraat 12", "countryCode": "NL"}}}
        markup = '<title>Peugeot Boxer L2H2</title><script type="application/ld+json">' + json.dumps(primary) + '</script><script id="__NEXT_DATA__">' + json.dumps(state) + '</script>'
        def evidence(page):
            return enrich(page, lambda _: {"code": "Ok", "routes": [{"distance": 25000}]},
                          lambda _: {"response": {"docs": [{"postcode": "4611AA", "huisnummer": 12, "centroide_ll": "POINT(4.31 51.51)"}]}})
        with patch("discover_listings.enrich", side_effect=evidence):
            candidate = extract("Boxer", URL, "AutoScout24", markup)
        requirements = {"available_payload_kg": 500, "internal_height_cm": 180, "internal_length_cm": 300}
        row = {"plate": "AB123C", "listing_url": URL, "reviewer": "Fictional independent inspector",
               "observed_at": "2000-01-01T00:00:00+00:00", "expires_at": "2100-01-01T00:00:00+00:00",
               "measurements": {key: {"value": value, "source_url": "https://example.test/fixture-report", "independently_checked": True} for key, value in requirements.items()},
               "checks": {key: {"confirmed": True, "method": "independent_inspection", "source_url": "https://example.test/fixture-report"} for key in ("cab_ac_working", "available_for_sale", "condition_acceptable")}}
        from specification_test_fixtures import add_conversion_fields
        add_conversion_fields(row)
        if alteration:
            alteration(row)
        discovery = {"candidates": [candidate], "source_coverage": {source: {} for source in SOURCE_NAMES},
                     "conversion_evidence": {"requirements": requirements, "assessments": [row]}}
        result = evaluate(discovery, lambda plate: {"status": "ok", "vehicle": {"status": "ok", "records": [{"kenteken": plate}]}, "defects": {"status": "ok", "records": []}})
        self.assertTrue(summarize(discovery, result)["validation_passed"])
        return result

    def test_detail_to_price_route_review_rdw_and_report(self):
        result = self.exercise()
        self.assertEqual(result["qualifiers"], 1)
        self.assertIn("1 bevestigde matches", render_html(result))
        self.assertEqual(result["results"][0]["candidate"]["price_incl_vat"], 5748)

    def test_incomplete_stale_failed_and_advertised_only_proof_cannot_qualify(self):
        changes = [lambda row: row["checks"]["cab_ac_working"].update(method="advertised_equipment"),
                   lambda row: row["checks"]["available_for_sale"].update(confirmed=False),
                   lambda row: row.update(expires_at="2001-01-01T00:00:00+00:00"),
                   lambda row: row["measurements"].pop("available_payload_kg")]
        for change in changes:
            self.assertEqual(self.exercise(change)["qualifiers"], 0)
