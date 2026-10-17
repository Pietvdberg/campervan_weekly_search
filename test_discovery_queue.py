import json
from pathlib import Path
import unittest
from unittest.mock import patch

from discovery_queue import cards, key, select, budget_applied
from discover_listings import discover, valid_url

BASE = "https://www.autoscout24.nl/lst/peugeot/boxer?priceto=8000"


def markup(listings):
    return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({"props": {"pageProps": {"pageQuery": {"priceto": "8000"}, "listings": listings}}}) + '</script>'


def card(number, price, variant="L2H2 Airco"):
    return {"url": "/aanbod/peugeot-boxer-00000000-0000-0000-0000-" + str(number).zfill(12),
            "title": "Peugeot Boxer", "vehicle": {"modelVersionInput": variant},
            "price": {"priceRaw": price, "priceFormatted": "€ " + str(price)}}


class DiscoveryQueueTests(unittest.TestCase):
    def test_expensive_and_damaged_cards_do_not_consume_detail_budget(self):
        data = markup([card(1, 25000), card(2, 6000), card(3, 1000, "L2H2 motor vast")])
        evidence = cards(data, BASE)
        pairs = [(row["title"], row["url"]) for row in evidence.values()]
        queue, rejected = select(pairs, evidence, lambda url: valid_url(url, "AutoScout24"))
        self.assertEqual(len(queue), 1)
        self.assertTrue(queue[0][1].endswith("000000000002"))
        self.assertEqual(len(rejected), 2)
        self.assertEqual(evidence[key(queue[0][1])]["evidence"], "unverified inventory card only")

    def test_affordable_card_precedes_unknown_price_and_low_roof_is_removed(self):
        data = markup([card(1, 6000, "L1H1"), card(2, 6000), card(3, None)])
        evidence = cards(data, BASE)
        queue, rejected = select([(row["title"], row["url"]) for row in evidence.values()], evidence, lambda _: True)
        self.assertTrue(queue[0][1].endswith("000000000002"))
        self.assertEqual(len(queue), 2)
        self.assertEqual(rejected[0]["reason"], "explicit low-roof configuration")

    def test_conflicting_prices_do_not_discard_a_possibly_affordable_advert(self):
        evidence = cards(markup([card(1, 20000), card(1, 6000)]), BASE)
        self.assertIsNone(next(iter(evidence.values()))["advertised_eur"])

    def test_query_parameter_alone_does_not_confirm_filter_application(self):
        self.assertFalse(budget_applied('<p>No usable filter state</p>'))
        self.assertTrue(budget_applied(markup([])))

    def test_unknown_tax_does_not_disqualify_affordable_inventory_lead(self):
        data = markup([card(1, 8000)])
        evidence = cards(data, BASE)
        queue, rejected = select([(row["title"], row["url"]) for row in evidence.values()], evidence, lambda _: True)
        self.assertEqual(len(queue), 1)
        self.assertFalse(rejected)
        self.assertNotIn("price_incl_vat", next(iter(evidence.values())))

    def test_modern_autotrack_uuid_is_an_individual_url(self):
        url = "https://www.autotrack.nl/a/peugeot-boxer-diesel-6e653a4f-1474-4e03-87f5-2e4736c50a4e"
        self.assertTrue(valid_url(url, "AutoTrack"))
        self.assertFalse(valid_url(url.replace("autotrack.nl", "autotrack.nl.evil.test"), "AutoTrack"))

    def test_discovery_visits_affordable_listing_before_detail_cap(self):
        data = markup([card(1, 25000), card(2, 6000)])
        visited = []
        def fetcher(url):
            visited.append(url)
            if "bing.com" in url:
                return "<rss><channel/></rss>", "application/rss+xml"
            if "/lst/" in url:
                return data, "text/html"
            return "<title>Peugeot Boxer L2H2 Airco</title>", "text/html"
        with patch.dict("discover_listings.SOURCES", {"AutoScout24": "autoscout24.nl"}, clear=True):
            result = discover(fetcher=fetcher, max_per_source=1)
        self.assertEqual(result["source_coverage"]["AutoScout24"]["attempts"], 1)
        self.assertTrue(result["candidates"][0]["listing_url"].endswith("000000000002"))
        self.assertFalse(any(url.endswith("000000000001") for url in visited))
        self.assertTrue(result["source_coverage"]["AutoScout24"]["budget_filter_confirmed"])

    def test_injector_damage_is_excluded_but_no_damage_is_not(self):
        rows = [("Peugeot Boxer L2H2 injectoren defect", "https://example.test/boxer-one"),
                ("Peugeot Boxer L2H2 geen schade", "https://example.test/boxer-two")]
        queue, rejected = select(rows, {}, lambda _: True)
        self.assertEqual(len(queue), 1)
        self.assertTrue(queue[0][1].endswith("two"))
        self.assertEqual(len(rejected), 1)
