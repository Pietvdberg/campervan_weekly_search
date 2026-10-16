import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree.ElementTree import ElementTree
from autowereld_snapshot import FEEDS, collect, read_snapshot, parse_rss

AD="https://www.autowereld.nl/peugeot/boxer/l2h2-airco-43922209/details.html"
RSS="<rss><channel><item><title>Peugeot Boxer L2H2</title><link>"+AD+"</link><pubDate>Fri, 16 Oct 2026 22:25:44 +0200</pubDate></item></channel></rss>"

class SnapshotTests(unittest.TestCase):
    def test_collect_rejects_fallback(self):
        with self.assertRaises(ValueError):
            collect(fetcher=lambda _: "<html><title>Try again</title></html>")
    def test_collector_requires_all_feeds(self):
        def partial(url):
            if url==FEEDS[0]:return RSS
            raise OSError("offline")
        with self.assertRaises(ValueError):
            collect(fetcher=partial)
    def test_fresh_snapshot_index_only(self):
        now=datetime(2026,10,16,20,tzinfo=timezone.utc)
        snapshot=collect(fetcher=lambda _: RSS,now=now)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"feed.json"
            path.write_text(json.dumps(snapshot),encoding="utf-8")
            pairs,status=read_snapshot(path,now=now+timedelta(hours=2))
            self.assertEqual(status,"fresh_index_only")
            self.assertEqual(pairs,[(AD,"Peugeot Boxer L2H2")])
            _,old=read_snapshot(path,now=now+timedelta(hours=49))
            self.assertEqual(old,"stale_or_future")
    def test_external_domain_rejected(self):
        now=datetime.now(timezone.utc)
        snapshot=collect(fetcher=lambda _: RSS,now=now)
        snapshot["entries"][0]["url"]="https://evil.example/peugeot/boxer/l2h2-airco-43922209/details.html"
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"feed.json"
            path.write_text(json.dumps(snapshot),encoding="utf-8")
            pairs,status=read_snapshot(path,now=now)
            self.assertEqual(pairs,[])
            self.assertEqual(status,"invalid_url")
    def test_plain_html_is_not_rss(self):
        with self.assertRaises(ValueError):
            parse_rss("<html><body>Boxer</body></html>")
if __name__=="__main__":
    unittest.main()
