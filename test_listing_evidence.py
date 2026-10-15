import unittest
from listing_evidence import structured,parse_amount,price_evidence,enrich,route_km

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
if __name__=="__main__":unittest.main()
