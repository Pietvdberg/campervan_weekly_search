import unittest
from discover_listings import SOURCES,discover,extract,valid_url

class DiscoveryTests(unittest.TestCase):
    def test_nine_sources(self): self.assertEqual(len(SOURCES),9)
    def test_not_listing(self): self.assertFalse(valid_url("https://www.marktplaats.nl/l/auto-s/bestelauto-s/","Marktplaats"))
    def test_listing(self): self.assertTrue(valid_url("https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123456-test","Marktplaats"))
    def test_wrong_host(self): self.assertFalse(valid_url("https://evil.test/v/auto-s/bestelauto-s/m123456-test","Marktplaats"))
    def test_vat_and_distance_unknown(self):
        c=extract("Peugeot Boxer L2H2 airco","https://www.marktplaats.nl/v/auto-s/bestelauto-s/m12345-test",
                  "Marktplaats","<html><title>Peugeot Boxer L2H2 airco</title><p>Roosendaal € 6000</p></html>")
        self.assertIsNone(c["checks"]["distance_within_100km"])
        self.assertIsNone(c["checks"]["price_incl_vat_within_8000"])
        self.assertFalse(c["plate_confirmed_from_listing"])
    def test_missing_sources_reported(self):
        def error(url): raise OSError("offline")
        d=discover(fetcher=error)
        self.assertEqual(len(d["source_coverage"]),9)
        self.assertTrue(all(v["status"]=="unavailable" for v in d["source_coverage"].values()))
    def test_missing_payload_cannot_be_claimed_suitable(self):
        c=extract("Peugeot Boxer L2H2 airco","https://www.marktplaats.nl/v/auto-s/bestelauto-s/m12345-test",
                  "Marktplaats","<html><title>Peugeot Boxer L2H2 airco</title></html>")
        self.assertIsNone(c["checks"]["conversion_suitable"])
    def test_failed_listing_fetch_is_not_candidate(self):
        rss="<rss><channel><item><title>Boxer L2H2</title><link>https://www.marktplaats.nl/v/auto-s/bestelauto-s/m12345-x</link></item></channel></rss>"
        def f(url):
            if "bing.com" in url:return rss,"application/rss+xml"
            raise OSError("blocked")
        self.assertEqual(discover(fetcher=f)["candidates"],[])

if __name__=="__main__":unittest.main()
