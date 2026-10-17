import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from source_access import SourceFetch, SourceStopped, host_key
from discover_listings import discover, SEED_PAGES, AUTOWERELD_RSS


class AccessTests(unittest.TestCase):
    def test_budget_is_shared_by_www_and_bare_host(self):
        calls = []
        guarded = SourceFetch(lambda url: calls.append(url), maximum_per_host=1)
        guarded("https://www.example.test/one")
        with self.assertRaises(SourceStopped):
            guarded("https://example.test/two")
        guarded("https://other.test/one")
        self.assertEqual(len(calls), 2)

    def test_http_denial_stops_host_without_stopping_other_hosts(self):
        for code in (403, 429):
            calls = []
            def denied(url):
                calls.append(url)
                raise HTTPError(url, code, "denied", {}, None)
            guarded = SourceFetch(denied)
            with self.assertRaises(HTTPError):
                guarded("https://www.example.test/seed")
            with self.assertRaises(SourceStopped):
                guarded("https://example.test/detail")
            self.assertEqual(len(calls), 1)
            self.assertEqual(guarded.restrictions(["https://example.test"])["example.test"]["http_status"], code)

    def test_seed_denial_stops_feeds_and_shared_dealer_source(self):
        for code in (403, 429):
            calls = []
            def fetcher(url):
                calls.append(url)
                if "autowereld.nl" in url:
                    raise HTTPError(url, code, "denied", {}, None)
                if "bing.com" in url:
                    return "<rss><channel/></rss>", "application/rss+xml"
                raise OSError("offline")
            with patch("discover_listings.read_snapshot_records", return_value=([], "not_supplied")):
                result = discover(fetcher)
            self.assertEqual(sum(host_key(url) == "autowereld.nl" for url in calls), 1)
            self.assertTrue(any("vanmossel.nl" in url for url in calls))
            coverage = result["source_coverage"]["AutoWereld"]
            self.assertEqual(coverage["status"], "source_unavailable")
            self.assertIn(str(code), coverage["source_block_reason"])
            self.assertEqual(coverage["rate_limited"], code == 429)

    def test_feed_denial_stops_remaining_feeds_and_detail_fetches(self):
        detail = "https://www.autowereld.nl/peugeot/boxer/l2h2-12345/details.html"
        calls = []
        def fetcher(url):
            calls.append(url)
            if url in AUTOWERELD_RSS:
                raise HTTPError(url, 429, "limited", {}, None)
            if "bing.com" in url:
                return "<rss><channel/></rss>", "application/rss+xml"
            if url in SEED_PAGES["AutoWereld"]:
                return f'<a href="{detail}">Boxer</a>', "text/html"
            raise OSError("offline")
        with patch("discover_listings.read_snapshot_records", return_value=([], "not_supplied")):
            result = discover(fetcher)
        self.assertEqual(sum(url in AUTOWERELD_RSS for url in calls), 1)
        self.assertNotIn(detail, calls)
        self.assertTrue(result["source_coverage"]["AutoWereld"]["rate_limited"])

    def test_error_message_containing_429_does_not_block_a_host(self):
        def fetcher(url):
            raise OSError("failed request number 429")
        guarded = SourceFetch(fetcher)
        for _ in range(2):
            with self.assertRaises(OSError):
                guarded("https://example.test/seed")
        self.assertEqual(guarded.stops, {})
        self.assertEqual(guarded.counts["example.test"], 2)
