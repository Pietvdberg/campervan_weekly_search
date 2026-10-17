import unittest
from listing_evidence import structured,parse_amount,price_evidence,enrich,route_km,pdok_coordinates

class EvidenceTests(unittest.TestCase):
    def test_european_money(self):
        self.assertEqual(float(parse_amount("6.950,00")),6950)
        self.assertEqual(float(parse_amount("6950.00")),6950)
    def test_vat_exclusive(self):
        d=enrich("<p>Prijs € 7.000 excl btw</p>")
        self.assertEqual(d["vat"]["amount_incl_vat"],8470)
        self.assertFalse(d["checks"]["price_incl_vat_within_8000"])
    def test_margin(self):
        d=enrich("<p>€ 7.500 marge</p>")
        self.assertEqual(d["vat"]["amount_incl_vat"],7500)
        self.assertTrue(d["checks"]["price_incl_vat_within_8000"])
    def test_vat_unspecified_is_unknown(self):
        d=enrich("<p>€ 7.000</p>")
        self.assertIsNone(d["vat"]["amount_incl_vat"])
        self.assertNotIn("price_incl_vat_within_8000",d["checks"])
    def test_jsonld_parsed(self):
        markup='<script type="application/ld+json">{"@type":"Car","name":"Boxer","offers":{"price":"7000","priceCurrency":"EUR"},"geo":{"latitude":51.52,"longitude":4.30}}</script><p>€ 7000 incl btw</p>'
        objs=structured(markup)
        self.assertTrue(any(d.get("name")=="Boxer" for d in objs))
        d=enrich(markup,lambda url:{"code":"Ok","routes":[{"distance":25000}]})
        self.assertEqual(d["distance_km"],25.0)
        self.assertTrue(d["checks"]["distance_within_100km"])
        self.assertTrue(d["checks"]["price_incl_vat_within_8000"])
    def test_route_failure_leaves_unknown(self):
        markup='<script type="application/ld+json">{"geo":{"latitude":51.52,"longitude":4.30}}</script>'
        def offline(url):raise OSError("routing unavailable")
        self.assertNotIn("distance_within_100km",enrich(markup,offline)["checks"])
    def test_far_route_excluded(self):
        markup='<script type="application/ld+json">{"geo":{"latitude":52.1,"longitude":5.1}}</script>'
        d=enrich(markup,lambda url:{"code":"Ok","routes":[{"distance":130000}]})
        self.assertFalse(d["checks"]["distance_within_100km"])
    def test_vat_before_price(self):
        d=enrich("<p>Prijs inclusief BTW: € 6.900</p>")
        self.assertEqual(d["vat"]["amount_incl_vat"],6900)
        self.assertEqual(d["vat"]["source"],"adjacent_seller_text")

    def test_exclusive_before_price(self):
        d=enrich("<p>Prijs excl. btw € 7.500</p>")
        self.assertEqual(d["vat"]["amount_incl_vat"],9075)
        self.assertFalse(d["checks"]["price_incl_vat_within_8000"])

    def test_unrelated_explicit_price_must_not_verify_other_offer(self):
        markup='<script type="application/ld+json">{"@type":"Offer","price":"7000","priceCurrency":"EUR"}</script><p>€ 5000 incl btw</p>'
        d=enrich(markup)
        self.assertIsNone(d["vat"]["amount_incl_vat"])

    def test_pdok_verified_postcode_address_driving_route(self):
        markup='''<script type="application/ld+json">{"@type":"Vehicle","address":{"postalCode":"4611 AA","streetAddress":"Voorbeeldstraat 12","addressCountry":"NL"}}</script>'''
        def pdok(url):
            self.assertIn("4611AA",url)
            return {"response":{"docs":[{"postcode":"4611 AA","huisnummer":12,"centroide_ll":"POINT(4.31 51.51)"}]}}
        d=enrich(markup,lambda url:{"code":"Ok","routes":[{"distance":34200}]},pdok)
        self.assertEqual(d["distance_km"],34.2)
        self.assertEqual(d["location_source"],"pdok_verified_full_address")

    def test_pdok_different_house_number_not_accepted(self):
        lookup=lambda url:{"response":{"docs":[{"postcode":"4611 AA","huisnummer":14,"centroide_ll":"POINT(4.31 51.51)"}]}}
        self.assertIsNone(pdok_coordinates(("4611AA","12"),lookup))

    def test_postcode_without_house_number_remains_unknown(self):
        markup='<script type="application/ld+json">{"address":{"postalCode":"4611 AA","addressLocality":"Bergen op Zoom"}}</script>'
        d=enrich(markup,lambda _:self.fail("Should not calculate a route"))
        self.assertIsNone(d["distance_km"])
if __name__=="__main__":unittest.main()

class AddressSuffixTests(unittest.TestCase):
    def test_house_letter_preserved_and_matched_exactly(self):
        from listing_evidence import address_from_structured
        address = address_from_structured([{"address": {"postalCode": "4611AA", "streetAddress": "Voorbeeldstraat 12b"}}])
        self.assertEqual(address, ("4611AA", "12B"))
        wrong = {"postcode": "4611AA", "huisnummer": 12, "huisletter": "A", "centroide_ll": "POINT(4.31 51.51)"}
        right = {**wrong, "huisletter": "B"}
        self.assertIsNone(pdok_coordinates(address, lambda _: {"response": {"docs": [wrong]}}))
        self.assertEqual(pdok_coordinates(address, lambda _: {"response": {"docs": [wrong, right]}}), (4.31, 51.51))

class BudgetLowerBoundTests(unittest.TestCase):
    def test_primary_eur_offer_over_limit_fails_without_inventing_vat(self):
        page = '<script type="application/ld+json">{"@type":"Offer","price":9000,"priceCurrency":"EUR"}</script>'
        result = enrich(page)
        self.assertFalse(result["checks"]["price_incl_vat_within_8000"])
        self.assertIsNone(result["vat"]["amount_incl_vat"])
        self.assertEqual(result["vat"]["basis"], "unknown")

    def test_offer_at_limit_remains_unknown_without_vat_basis(self):
        page = '<script type="application/ld+json">{"@type":"Offer","price":8000,"priceCurrency":"EUR"}</script>'
        self.assertNotIn("price_incl_vat_within_8000", enrich(page)["checks"])

    def test_unrelated_visible_price_does_not_override_selected_offer(self):
        page = '<script type="application/ld+json">{"@type":"Offer","price":7000,"priceCurrency":"EUR"}</script><p>Other vehicle € 9000 incl btw</p>'
        self.assertNotIn("price_incl_vat_within_8000", enrich(page)["checks"])

    def test_non_eur_offer_does_not_supply_eur_lower_bound(self):
        page = '<script type="application/ld+json">{"@type":"Offer","price":9000,"priceCurrency":"USD"}</script>'
        self.assertNotIn("price_incl_vat_within_8000", enrich(page)["checks"])
