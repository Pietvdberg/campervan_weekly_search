import unittest
from inventory_discovery import classify,crawl,links_on_page

ROOT="https://www.gaspedaal.nl/peugeot/boxer"
DETAIL="https://www.gaspedaal.nl/auto/peugeot/boxer/offer-12345"
OTHER="https://www.gaspedaal.nl/auto/ford/transit/offer-54321"

class InventoryTests(unittest.TestCase):
    def test_category_not_advert(self):
        self.assertEqual(classify(ROOT,"Gaspedaal"),"inventory")
        self.assertEqual(classify("https://www.gaspedaal.nl/auto/peugeot/boxer","Gaspedaal"),"inventory")
        self.assertEqual(classify(DETAIL,"Gaspedaal"),"detail")
    def test_other_domain_ignored(self):
        page=f'<a href="https://other.test/auto/peugeot/boxer/123">Boxer</a><a href="{DETAIL}">Boxer</a>'
        result=crawl("Gaspedaal",[ROOT],lambda _: (page,"text/html"))
        self.assertEqual(list(result["details"]),[DETAIL])
    def test_pagination_and_deduplication(self):
        second=ROOT+"?page=2"
        calls=[]
        pages={
          ROOT:f'<a href="{DETAIL}">Peugeot Boxer L2H2</a><a href="{second}" rel="next">Volgende</a>',
          second:f'<a href="{DETAIL}">Peugeot Boxer</a><a href="{OTHER}">Ford Transit</a>'
        }
        def fetch(url):
            calls.append(url)
            return pages[url],"text/html"
        result=crawl("Gaspedaal",[ROOT],fetch)
        self.assertEqual(set(result["details"]),{DETAIL,OTHER})
        self.assertEqual(result["inventory_pages_accessible"],2)
        self.assertEqual(calls,[ROOT,second])
    def test_no_results_means_unverified_inventory(self):
        result=crawl("Gaspedaal",[ROOT],lambda _:('<p>Boxer aanbiedingen</p>',"text/html"))
        self.assertEqual(result["details"],{})
        self.assertTrue(result["inventory_diagnostics"])
    def test_rate_limit_stops_traversal(self):
        from urllib.error import HTTPError
        def blocked(url):raise HTTPError(url,429,"Too many requests",{},None)
        result=crawl("Gaspedaal",[ROOT,ROOT+"?page=2"],blocked)
        self.assertEqual(result["inventory_pages_checked"],1)
        self.assertEqual(result["inventory_pages_accessible"],0)
    def test_embedded_json_detail_links(self):
        page='<script type="application/ld+json">{"@type":"ItemList","itemListElement":[{"url":"'+DETAIL+'","name":"Peugeot Boxer"}]}</script>'
        found=crawl("Gaspedaal",[ROOT],lambda _: (page,"text/html"))
        self.assertIn(DETAIL,found["details"])
    def test_detail_attempt_budget_separate_from_inventory_pages(self):
        from unittest.mock import patch
        from discover_listings import discover,SEED_PAGES
        html_page='<a href="'+DETAIL+'">Peugeot Boxer L2H2</a>'
        vehicle='<title>Peugeot Boxer L2H2</title><script type="application/ld+json">{"@type":"Vehicle","name":"Peugeot Boxer","offers":{"price":"7000"}}</script>'
        def fetch(url):
            if "bing.com" in url:return "<rss><channel/></rss>","application/rss+xml"
            if url==DETAIL:return vehicle,"text/html"
            if url in SEED_PAGES["Gaspedaal"]:return html_page,"text/html"
            raise OSError("offline")
        result=discover(fetcher=fetch)
        g=result["source_coverage"]["Gaspedaal"]
        self.assertEqual(g["attempts"],1)
        self.assertEqual(g["individual_pages_fetched"],1)
        self.assertGreaterEqual(g["inventory_pages_checked"],1)
    def test_missing_inventory_is_not_zero_stock(self):
        from discover_listings import discover
        result=discover(fetcher=lambda _: (_ for _ in ()).throw(OSError("offline")))
        self.assertEqual(result["source_coverage"]["Gaspedaal"]["status"],"source_unavailable")
if __name__=="__main__":unittest.main()
