import unittest
from urllib.error import HTTPError
from inventory_discovery import classify, crawl

ROOT = "https://www.viabovag.nl/auto/merk-peugeot/model-boxer/occasion"
DETAIL = "https://www.viabovag.nl/auto/aanbod/peugeot-boxer-l2h2-9uh42eg"
OTHER = "https://www.viabovag.nl/auto/aanbod/ford-transit-l2h2-7ab123c"

class InventoryTests(unittest.TestCase):
    def test_listing_and_inventory_distinction(self):
        self.assertEqual(classify(ROOT, "viaBOVAG"), "inventory")
        self.assertEqual(classify(DETAIL, "viaBOVAG"), "detail")
        self.assertIsNone(classify("https://www.viabovag.nl/auto/occasion", "viaBOVAG"))
    def test_discovers_only_on_domain(self):
        page = '<a href="' + DETAIL + '">Peugeot Boxer</a><a href="https://other.test/auto/aanbod/ford-transit-123456">Ford Transit</a>'
        result = crawl("viaBOVAG", [ROOT], lambda _: (page, "text/html"))
        self.assertEqual(list(result["details"]), [DETAIL])
    def test_pagination_deduplicates(self):
        second = ROOT + "?page=2"
        pages = {
            ROOT: '<a href="' + DETAIL + '">Peugeot Boxer</a><a rel="next" href="' + second + '">Volgende</a>',
            second: '<a href="' + DETAIL + '">Peugeot Boxer</a><a href="' + OTHER + '">Ford Transit</a>'
        }
        result = crawl("viaBOVAG", [ROOT], lambda url: (pages[url], "text/html"))
        self.assertEqual(set(result["details"]), {DETAIL, OTHER})
        self.assertEqual(result["inventory_pages_accessible"], 2)
    def test_unverified_inventory_not_no_stock(self):
        result = crawl("viaBOVAG", [ROOT], lambda _: ("<p>Vehicle search</p>", "text/html"))
        self.assertEqual(result["details"], {})
        self.assertTrue(result["inventory_diagnostics"])
    def test_rate_limit_stops(self):
        def blocked(url): raise HTTPError(url, 429, "Too Many Requests", {}, None)
        result = crawl("viaBOVAG", [ROOT, ROOT + "?page=2"], blocked)
        self.assertEqual(result["inventory_pages_checked"], 1)
        self.assertEqual(result["inventory_pages_accessible"], 0)
    def test_embedded_json_detail_links(self):
        markup = '<script type="application/ld+json">{"@type":"ItemList","itemListElement":[{"url":"' + DETAIL + '","name":"Peugeot Boxer"}]}</script>'
        result = crawl("viaBOVAG", [ROOT], lambda _: (markup, "text/html"))
        self.assertIn(DETAIL, result["details"])
    def test_detail_attempts_not_inventory_pages(self):
        from discover_listings import discover, SEED_PAGES
        listing = '<title>Peugeot Boxer L2H2</title><script type="application/ld+json">{"@type":"Vehicle","name":"Peugeot Boxer","offers":{"price":"7000"}}</script>'
        def fetch(url):
            if "bing.com" in url: return "<rss><channel/></rss>", "application/rss+xml"
            if url == DETAIL: return listing, "text/html"
            if url in SEED_PAGES["viaBOVAG"]: return '<a href="' + DETAIL + '">Peugeot Boxer</a>', "text/html"
            raise OSError("offline")
        result = discover(fetcher=fetch)
        coverage = result["source_coverage"]["viaBOVAG"]
        self.assertEqual(coverage["attempts"], 1)
        self.assertEqual(coverage["individual_pages_fetched"], 1)
        self.assertGreaterEqual(coverage["inventory_pages_checked"], 1)
    def test_source_unavailable_not_no_stock(self):
        from discover_listings import discover
        def offline(url): raise OSError("offline")
        result = discover(fetcher=offline)
        self.assertEqual(result["source_coverage"]["viaBOVAG"]["status"], "source_unavailable")

if __name__ == "__main__":
    unittest.main()
