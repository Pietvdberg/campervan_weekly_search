import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from dealer_sources import load_registry, dealer_for_url, crawl_dealers
from source_access import SourceFetch


class DealerSourceTests(unittest.TestCase):
    def dealer(self, host="dealer.test", name="local"):
        return {"id": name, "name": name, "domain": host, "inventory_url": "https://" + host + "/inventory",
                "contact_url": "https://" + host + "/contact", "detail_path_pattern": "^/vehicle/[0-9]+-boxer$", "checked_on": "2026-10-17"}

    def test_only_registered_individual_paths_are_accepted(self):
        registry = [self.dealer()]
        self.assertIsNotNone(dealer_for_url("https://dealer.test/vehicle/123-boxer", registry, detail=True))
        for url in ("https://dealer.test/inventory", "https://dealer.test.evil.test/vehicle/123-boxer", "http://dealer.test/vehicle/123-boxer"):
            self.assertIsNone(dealer_for_url(url, registry, detail=True))

    def test_registry_rejects_cross_domain_inventory_or_unanchored_pattern(self):
        for change in ({"inventory_url": "https://other.test/inventory"}, {"detail_path_pattern": "vehicle"}):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "dealers.json"
                path.write_text(json.dumps([{**self.dealer(), **change}]))
                with self.assertRaises(ValueError):
                    load_registry(path)

    def test_direct_inventory_does_not_depend_on_a_marketplace(self):
        registry = [self.dealer()]
        def fetch(url):
            return '<a href="/vehicle/123-boxer">€ 6000 Peugeot Boxer L2H2 Airco</a><a href="https://other.test/vehicle/999-boxer">Boxer</a>', "text/html"
        result = crawl_dealers(fetch, registry=registry)
        self.assertEqual(list(result["details"]), ["https://dealer.test/vehicle/123-boxer"])
        self.assertEqual(next(iter(result["cards"].values()))["advertised_eur"], 6000)
        self.assertEqual(result["coverage"][0]["status"], "inventory_accessible")
        self.assertNotIn("distance_km", result["coverage"][0])

    def test_failed_dealer_does_not_hide_another_accessible_dealer(self):
        registry = [self.dealer(), self.dealer("second.test", "second")]
        def fetch(url):
            if "dealer.test" in url:
                raise HTTPError(url, 403, "denied", {}, None)
            return '<a href="/vehicle/123-boxer">Boxer</a>', "text/html"
        result = crawl_dealers(SourceFetch(fetch), registry=registry)
        self.assertEqual([row["status"] for row in result["coverage"]], ["source_unavailable", "inventory_accessible"])

    def test_pagination_is_bounded_and_stays_on_inventory_path(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return '<a href="/inventory?page=2" rel="next">Next</a><a href="/contact" rel="next">Next</a>', "text/html"
        result = crawl_dealers(fetch, maximum_pages=1, registry=[self.dealer()])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["coverage"][0]["inventory_pages_pending"], 1)

    def test_real_registry_loads_as_three_independently_maintained_sources(self):
        registry = load_registry()
        self.assertEqual(len({row["id"] for row in registry}), 3)
        self.assertTrue(any(row["domain"] == "bwcr.nl" for row in registry))
        self.assertTrue(all(row.get("contact_url") and row.get("checked_on") for row in registry))

    def test_registered_detail_requires_matching_form_and_gallery_identity(self):
        from listing_identity import bind_evidence
        url = "https://www.bwcr.nl/occasions-kopen/56710118-mercedes-benz-sprinter"
        page = '<main><h1>Mercedes Sprinter L2H2</h1><img src="/webservices/feed_images/56710118/photo.jpg"><form id="car_details_form1" action="' + url + '"></form><p>Kenteken V09RJG</p></main>'
        scoped, provenance = bind_evidence(page, url)
        self.assertEqual(provenance["status"], "bound")
        self.assertEqual(provenance["basis"], "registered_dealer_form_gallery")
        self.assertIn("V09RJG", scoped)
        for altered in (page.replace("feed_images/56710118", "feed_images/99999999"), page.replace('action="' + url, 'action="https://www.bwcr.nl/occasions-kopen/99999999-other')):
            self.assertEqual(bind_evidence(altered, url)[1]["status"], "unbound")
        self.assertEqual(bind_evidence(page.replace(url, url.replace('bwcr.nl', 'other.test')), url.replace('bwcr.nl', 'other.test'))[1]["status"], "unbound")

    def test_dealer_net_price_over_gross_budget_is_only_an_index_exclusion(self):
        from discovery_queue import select
        def fetch(url):
            return '<a href="/vehicle/123-boxer">€ 7950,- ex. BTW Peugeot Boxer L2H2</a>', "text/html"
        result = crawl_dealers(fetch, registry=[self.dealer()])
        entry = next(iter(result["cards"].values()))
        self.assertEqual(entry["advertised_eur"], 7950)
        self.assertAlmostEqual(entry["gross_lower_bound_eur"], 9619.5)
        queue, excluded = select([(title, url) for url, title in result["details"].items()], result["cards"], lambda _: True)
        self.assertFalse(queue)
        self.assertEqual(len(excluded), 1)
        self.assertNotIn("price_incl_vat", entry)
