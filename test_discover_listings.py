import unittest
from unittest.mock import patch
from discover_listings import SOURCES,discover,extract,valid_url

class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        # Offline synthetic discovery tests must not depend on a snapshot
        # checked into the repo by the Raspberry Pi collector.
        self.snapshot_patch=patch('discover_listings.read_snapshot_records',return_value=([], 'not_supplied'))
        self.snapshot_patch.start()
        self.addCleanup(self.snapshot_patch.stop)
    def test_three_sources_have_individual_url_patterns(self):
        self.assertTrue(valid_url("https://www.autoscout24.nl/aanbod/peugeot-boxer-l2h2-diesel-wit-76517dc4-5b39-4637-af35-b89dca80173e","AutoScout24"))
        self.assertFalse(valid_url("https://www.autoscout24.nl/lst/peugeot/boxer","AutoScout24"))
        self.assertTrue(valid_url("https://www.autotrack.nl/a/peugeot-boxer-diesel-2017-60208674","AutoTrack"))
        self.assertFalse(valid_url("https://www.autotrack.nl/aanbod/merk/ford/model/transit","AutoTrack"))
    def test_new_marketplace_seed_pages(self):
        from discover_listings import SEED_PAGES
        self.assertIn("https://www.autotrack.nl/aanbod/merk/ford/model/transit",SEED_PAGES["AutoTrack"])
        self.assertIn("https://www.autoscout24.nl/lst/peugeot/boxer/ve_l2h2",SEED_PAGES["AutoScout24"])
    def test_direct_three_source_discovery(self):
        from discover_listings import SEED_PAGES
        ads={
            "AutoScout24":"https://www.autoscout24.nl/aanbod/peugeot-boxer-l2h2-diesel-wit-76517dc4-5b39-4637-af35-b89dca80173e",
            "AutoTrack":"https://www.autotrack.nl/a/peugeot-boxer-diesel-2017-60208674"
        }
        detail="<html><title>Peugeot Boxer L2H2 Airco</title><p>Roosendaal € 7000</p></html>"
        def fake(url):
            if "bing.com" in url: return "<rss><channel/></rss>","application/rss+xml"
            if url in ads.values():return detail,"text/html"
            for source in ads:
                if url in SEED_PAGES[source]:
                    return '<html><a href="'+ads[source]+'">Peugeot Boxer L2H2</a></html>',"text/html"
            raise OSError("not available")
        result=discover(fetcher=fake)
        for source in ads:
            self.assertEqual(result["source_coverage"][source]["individual_pages_fetched"],1,source)
    def test_remaining_source_detail_url_shapes(self):
        self.assertTrue(valid_url("https://www.autowereld.nl/peugeot/boxer/333-2-2-hdi-l2h2-42732187/details.html","AutoWereld"))
        self.assertFalse(valid_url("https://www.autowereld.nl/peugeot/boxer/_energy","AutoWereld"))
    def test_remaining_sources_do_not_misidentify_inventory(self):
        from discover_listings import SEED_PAGES
        for source in ("AutoWereld",):
            self.assertTrue(SEED_PAGES[source])
        self.assertNotIn("Gaspedaal",SEED_PAGES)
    def test_autowereld_inventory_yields_vehicle_detail(self):
        from discover_listings import discover,SEED_PAGES
        vehicle="https://www.autowereld.nl/peugeot/boxer/333-2-2-hdi-l2h2-42732187/details.html"
        def fake(url):
            if "bing.com" in url: return "<rss><channel/></rss>","application/rss+xml"
            if url==vehicle:return '<title>Peugeot Boxer L2H2</title><p>Airco 7000 euro</p>',"text/html"
            if url in SEED_PAGES["AutoWereld"]:return '<a href="'+vehicle+'">Peugeot Boxer L2H2</a>',"text/html"
            raise OSError("offline")
        from unittest.mock import patch
        # Isolate inventory behaviour from the independent live smoke-test seed.
        with patch.dict(SEED_PAGES, {"AutoWereld":[u for u in SEED_PAGES["AutoWereld"] if u != "https://www.autowereld.nl/peugeot/boxer/330-2-0-bluehdi-l2h2-premium-3-zitplaatsen-bluetooth-airco-cruise-43911117/details.html"]}):
            result=discover(fetcher=fake)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["individual_pages_fetched"],1)
    def test_autowereld_rss_discovery_without_html_cards(self):
        from discover_listings import discover, AUTOWERELD_RSS
        url="https://www.autowereld.nl/peugeot/boxer/335-l2h2-airco-43861106/details.html"
        rss='<rss><channel><item><title>Peugeot Boxer L2H2 Airco</title><link>'+url+'</link></item></channel></rss>'
        def fake(target):
            if target in AUTOWERELD_RSS:return rss if target==AUTOWERELD_RSS[0] else "<rss><channel/></rss>","application/rss+xml"
            if "bing.com" in target:return "<rss><channel/></rss>","application/rss+xml"
            if target==url:return "<title>Peugeot Boxer L2H2 Airco</title><p>€ 6500</p>","text/html"
            raise OSError("offline")
        result=discover(fetcher=fake)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["individual_pages_fetched"],1)
    def test_autowereld_malformed_rss_recovers_real_advert_url(self):
        from discover_listings import discover, AUTOWERELD_RSS
        url="https://www.autowereld.nl/peugeot/boxer/330-2-0-bluehdi-l2h2-premium-43911117/details.html"
        # Invalid XML must not erase real source-specific listing links.
        broken='<rss><channel><item><title>Peugeot Boxer & Airco</title><link>'+url+'</link></item><bad><</rss>'
        def fake(target):
            if target in AUTOWERELD_RSS:
                return (broken if target==AUTOWERELD_RSS[0] else "<rss><channel/></rss>"),"application/rss+xml"
            if "bing.com" in target:
                return "<rss><channel/></rss>","application/rss+xml"
            if target==url:
                return '<title>Peugeot Boxer L2H2 Airco</title>',"text/html"
            raise OSError("offline")
        result=discover(fetcher=fake)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["individual_pages_fetched"],1)
        self.assertIn(url,[c["listing_url"] for c in result["candidates"]])
    def test_autowereld_malformed_rss_ignores_external_urls(self):
        from discover_listings import discover, AUTOWERELD_RSS, SEED_PAGES
        fake_url="https://other-site.nl/peugeot/boxer/330-l2h2-43911117/details.html"
        def fake(target):
            if target in AUTOWERELD_RSS:
                return "<bad><"+fake_url,"application/rss+xml"
            if "bing.com" in target:
                return "<rss><channel/></rss>","application/rss+xml"
            raise OSError("offline")
        from unittest.mock import patch
        with patch.dict(SEED_PAGES, {"AutoWereld":[u for u in SEED_PAGES["AutoWereld"] if u != "https://www.autowereld.nl/peugeot/boxer/330-2-0-bluehdi-l2h2-premium-3-zitplaatsen-bluetooth-airco-cruise-43911117/details.html"]}):
            result=discover(fetcher=fake)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["attempts"],0)
    def test_autowereld_valid_xml_without_items_recovers_links(self):
        from discover_listings import discover, AUTOWERELD_RSS
        url="https://www.autowereld.nl/peugeot/boxer/330-2-0-bluehdi-l2h2-premium-43911117/details.html"
        xml="<rss><channel><description>Browse "+url+"</description></channel></rss>"
        def fake(target):
            if target in AUTOWERELD_RSS:
                return (xml if target==AUTOWERELD_RSS[0] else "<rss><channel/></rss>"),"application/rss+xml"
            if "bing.com" in target:return "<rss><channel/></rss>","application/rss+xml"
            if target==url:return "<title>Peugeot Boxer L2H2 Airco</title>","text/html"
            raise OSError("offline")
        data=discover(fetcher=fake)
        self.assertEqual(data["source_coverage"]["AutoWereld"]["individual_pages_fetched"],1)
        self.assertEqual(data["source_coverage"]["AutoWereld"]["feed_diagnostics"][0]["accepted_new_urls"],1)
    def test_autowereld_valid_feed_no_urls_reports_diagnostics(self):
        from discover_listings import discover, AUTOWERELD_RSS
        def fake(target):
            if target in AUTOWERELD_RSS or "bing.com" in target:
                return "<rss><channel/></rss>","application/rss+xml"
            raise OSError("offline")
        data=discover(fetcher=fake)
        self.assertEqual(data["source_coverage"]["AutoWereld"]["individual_pages_fetched"],0)
        self.assertEqual(data["source_coverage"]["AutoWereld"]["feed_diagnostics"][0]["accepted_new_urls"],0)
    def test_autowereld_live_smoke_seed_and_feed_diagnostics(self):
        from discover_listings import SEED_PAGES, AUTOWERELD_RSS, discover
        url="https://www.autowereld.nl/peugeot/boxer/330-2-0-bluehdi-l2h2-premium-3-zitplaatsen-bluetooth-airco-cruise-43911117/details.html"
        self.assertIn(url,SEED_PAGES["AutoWereld"])
        self.assertTrue(valid_url(url,"AutoWereld"))
        def fake(target):
            if target in AUTOWERELD_RSS:
                return "<!doctype html><html><title>Access unavailable</title></html>","text/html"
            if "bing.com" in target:
                return "<rss><channel/></rss>","application/rss+xml"
            if target==url:
                return "<title>Peugeot Boxer L2H2 Airco</title>","text/html"
            raise OSError("offline")
        result=discover(fetcher=fake)
        feed=result["source_coverage"]["AutoWereld"]["feed_diagnostics"][0]
        self.assertEqual(feed["content_type"],"text/html")
        self.assertIn("Access unavailable",feed["response_prefix"])
        self.assertEqual(result["source_coverage"]["AutoWereld"]["individual_pages_fetched"],1)
    def test_vanmossel_stock_url_vs_catalog(self):
        good="https://www.vanmossel.nl/van-mossel-bedrijfswagens/voorraad/225359584-1-volkswagen-crafter-35-20-tdi-l3h2-comfortline-diesel-2020"
        self.assertTrue(valid_url(good,"Local dealers"))
        self.assertFalse(valid_url("https://www.vanmossel.nl/van-mossel-bedrijfswagens/voorraad","Local dealers"))
    def test_autowereld_html_feed_is_not_misrepresented_as_rss(self):
        from discover_listings import AUTOWERELD_RSS,SEED_PAGES
        def fake(url):
            if "bing.com" in url:return "<rss><channel/></rss>","application/rss+xml"
            if url in AUTOWERELD_RSS:return "<html><title>Temporary response</title></html>","text/html"
            raise OSError("offline")
        data=discover(fetcher=fake)
        feed=data["source_coverage"]["AutoWereld"]["feed_diagnostics"][0]
        self.assertTrue(feed["unexpected_html"])
        self.assertFalse(feed["feed_usable"])
    def test_autowereld_html_feed_link_conversion(self):
        from discover_listings import AUTOWERELD_RSS,SEED_PAGES
        target="https://www.autowereld.nl/peugeot/boxer/l2h2-airco-43922209/details.html"
        html_page='<html><head><title>Peugeot Boxer offers</title></head><body><a href="'+target+'">Peugeot Boxer L2H2 Airco</a></body></html>'
        def fake(url):
            if url in AUTOWERELD_RSS:return html_page,"text/html"
            if url==target:return "<html><title>Peugeot Boxer L2H2 Airco</title></html>","text/html"
            if "bing.com" in url:return "<rss><channel/></rss>","application/rss+xml"
            raise OSError("offline")
        result=discover(fetcher=fake)
        self.assertIn(target,[c["listing_url"] for c in result["candidates"]])
        self.assertTrue(result["source_coverage"]["AutoWereld"]["feed_diagnostics"][0]["html_conversion"]["conversion_usable"])
    def test_autowereld_block_page_does_not_create_xml_listings(self):
        from discover_listings import AUTOWERELD_RSS
        def fake(url):
            if url in AUTOWERELD_RSS:return "<html><title>Temporarily unavailable</title><body>no listings</body></html>","text/html"
            if "bing.com" in url:return "<rss><channel/></rss>","application/rss+xml"
            raise OSError("offline")
        result=discover(fetcher=fake)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["feed_diagnostics"][0]["html_conversion"]["verified_advert_links"],0)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["individual_pages_fetched"],0)
    def test_six_sources(self):
        self.assertEqual(len(SOURCES),6)
        self.assertNotIn("wijkopenautos",SOURCES)
        self.assertNotIn("TrucksNL",SOURCES)
        self.assertNotIn("Bedrijfsauto",SOURCES)
    def test_not_listing(self): self.assertFalse(valid_url("https://www.marktplaats.nl/l/auto-s/bestelauto-s/","Marktplaats"))
    def test_listing(self): self.assertTrue(valid_url("https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123456-test","Marktplaats"))
    def test_all_sources_present(self):
        self.assertIn("AutoWereld",SOURCES)
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
        self.assertEqual(len(d["source_coverage"]),6)
        self.assertTrue(all(v["status"] in ("unavailable","source_unavailable") for v in d["source_coverage"].values()))
    def test_missing_payload_cannot_be_claimed_suitable(self):
        c=extract("Peugeot Boxer L2H2 airco","https://www.marktplaats.nl/v/auto-s/bestelauto-s/m12345-test",
                  "Marktplaats","<html><title>Peugeot Boxer L2H2 airco</title></html>")
        self.assertIsNone(c["checks"]["conversion_suitable"])
    def test_local_dealer_directory_is_not_a_vehicle_listing(self):
        self.assertFalse(valid_url("https://www.autowereld.nl/aanbieder/mana-bedrijfswagens-910447/auto.html","Local dealers"))
        self.assertFalse(valid_url("https://unrelated.nl/something/boxer","Local dealers"))
    def test_direct_marketplace_listing_works_without_bing(self):
        from discover_listings import SEED_PAGES
        target="https://www.marktplaats.nl/v/auto-s/bestelauto-s/m1234567-boxer"
        def fetcher(url):
            if "bing.com" in url: raise OSError("index offline")
            if url == target:
                return f'<html><head><title>Peugeot Boxer L2H2 airco</title><link rel="canonical" href="{target}"></head><main>Peugeot Boxer L2H2 airco Kenteken: V-360-SJ</main></html>',"text/html"
            if url in SEED_PAGES["Marktplaats"]:
                return '<html><a href="'+target+'">Boxer L2H2 airco</a></html>',"text/html"
            raise OSError("unavailable")
        data=discover(fetcher=fetcher)
        self.assertEqual(len(data["candidates"]),1)
        self.assertEqual(data["candidates"][0]["plate"],"V-360-SJ")
        self.assertEqual(data["source_coverage"]["Marktplaats"]["direct_eligible_urls"],1)
    def test_only_relevant_target_vans_enter_dealer_queue(self):
        from discover_listings import relevant_link
        self.assertFalse(relevant_link("Regional occasions","https://www.gaspedaal.nl/regio/occasions-alkmaar","Local dealers"))
        self.assertTrue(relevant_link("Peugeot Boxer L2H2","https://www.viabovag.nl/auto/aanbod/peugeot-boxer-123abc","viaBOVAG"))
    def test_single_structured_vehicle_is_valid(self):
        from discover_listings import extract
        page='<html><title>Peugeot Boxer L2H2</title><script type="application/ld+json">{"@type":"Vehicle","name":"Peugeot Boxer L2H2","offers":{"@type":"Offer","price":"7000"}}</script></html>'
        self.assertIsNotNone(extract("Peugeot Boxer","https://www.viabovag.nl/auto/aanbod/peugeot-boxer-123abc","viaBOVAG",page))
    def test_multiple_product_objects_are_not_a_detail(self):
        from discover_listings import extract
        page='<html><title>Boxer list</title><script type="application/ld+json">[{"@type":"Product","name":"Boxer A","offers":{"price":7000}},{"@type":"Product","name":"Boxer B","offers":{"price":7500}}]</script></html>'
        self.assertIsNone(extract("Peugeot Boxer","https://www.viabovag.nl/auto/aanbod/peugeot-boxer-123abc","viaBOVAG",page))
    def test_viabovag_requires_real_vehicle_detail_url(self):
        self.assertTrue(valid_url("https://www.viabovag.nl/auto/aanbod/ford-transit-290-22-tdci-l2h2-trend-9uh42eg","viaBOVAG"))
        self.assertFalse(valid_url("https://www.viabovag.nl/auto/merk-ford/model-transit/occasion","viaBOVAG"))
        self.assertFalse(valid_url("https://www.viabovag.nl/kamperen/voertuigsoort-camper/occasion","viaBOVAG"))
        self.assertFalse(valid_url("https://www.viabovag.nl/auto/hybride/plugin-hybride-ja","viaBOVAG"))
    def test_viabovag_model_search_not_individual_listing(self):
        self.assertFalse(valid_url("https://www.viabovag.nl/auto/merk-peugeot/model-boxer/occasion","viaBOVAG"))
    def test_targeted_seed_pages_exist(self):
        from discover_listings import SEED_PAGES
        self.assertNotIn("Gaspedaal",SEED_PAGES)
        self.assertNotIn("Gaspedaal",SOURCES)
        self.assertIn("https://www.viabovag.nl/auto/merk-peugeot/model-boxer/occasion",SEED_PAGES["viaBOVAG"])
    def test_auxiliary_pages_rejected(self):
        self.assertFalse(valid_url("https://www.gaspedaal.nl/regio/occasions-almere","Local dealers"))
    def test_category_pages_not_candidate_listings(self):
        self.assertFalse(valid_url("https://www.autotrack.nl/aanbod/carrosserievorm/suv","AutoTrack"))
        self.assertFalse(valid_url("https://www.viabovag.nl/auto/occasion","viaBOVAG"))
    def test_429_stops_requests_for_a_source(self):
        from urllib.error import HTTPError
        from discover_listings import SEED_PAGES
        targets=[f"https://www.marktplaats.nl/v/auto-s/bestelauto-s/m{90000+i}-boxer" for i in range(20)]
        count=[0]
        def fake(url):
            if "bing.com" in url: return "<rss><channel></channel></rss>","application/rss+xml"
            if url in SEED_PAGES["Marktplaats"]:
                return "<html>"+"".join(f'<a href="{t}">Boxer L2H2</a>' for t in targets)+"</html>","text/html"
            if url in targets:
                count[0]+=1
                raise HTTPError(url,429,"Too Many Requests",{},None)
            raise OSError("offline")
        result=discover(fetcher=fake)
        self.assertEqual(count[0],1)
        self.assertTrue(result["source_coverage"]["Marktplaats"]["rate_limited"])
    def test_failed_listing_fetch_is_not_candidate(self):
        rss="<rss><channel><item><title>Boxer L2H2</title><link>https://www.marktplaats.nl/v/auto-s/bestelauto-s/m12345-x</link></item></channel></rss>"
        def f(url):
            if "bing.com" in url:return rss,"application/rss+xml"
            raise OSError("blocked")
        self.assertEqual(discover(fetcher=f)["candidates"],[])

class SnapshotIngestionTests(unittest.TestCase):
    def test_fresh_snapshot_populates_only_unverified_rss_leads(self):
        import json
        import os
        import tempfile
        from datetime import datetime, timezone
        from pathlib import Path
        from autowereld_snapshot import collect
        from discover_listings import discover
        url="https://www.autowereld.nl/peugeot/boxer/l2h2-airco-43922209/details.html"
        rss="<rss><channel><item><title>Peugeot Boxer L2H2 Airco</title><link>"+url+"</link></item></channel></rss>"
        with tempfile.TemporaryDirectory() as temp:
            location=Path(temp)/"snapshot.json"
            location.write_text(json.dumps(collect(fetcher=lambda _:rss)),encoding="utf8")
            def fake(target):
                if "bing.com" in target:return "<rss><channel/></rss>","application/rss+xml"
                if target==url:raise OSError("HTTP 403: Access Denied")
                raise OSError("offline")
            with patch.dict(os.environ,{"AUTOWERELD_RSS_SNAPSHOT":str(location)}):
                result=discover(fetcher=fake)
        self.assertEqual(len(result["unverified_rss_leads"]),1)
        self.assertEqual(result["unverified_rss_leads"][0]["url"],url)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["external_rss_snapshot_status"],"fresh_index_only")
        self.assertEqual(result["source_coverage"]["AutoWereld"]["external_rss_urls_accepted"],1)
        self.assertEqual(result["source_coverage"]["AutoWereld"]["individual_pages_fetched"],0)
        self.assertFalse(any(x["listing_url"]==url for x in result["candidates"]))

if __name__=="__main__":unittest.main()
