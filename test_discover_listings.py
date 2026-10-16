import unittest
from discover_listings import SOURCES,discover,extract,valid_url

class DiscoveryTests(unittest.TestCase):
    def test_nine_sources(self): self.assertEqual(len(SOURCES),10)
    def test_not_listing(self): self.assertFalse(valid_url("https://www.marktplaats.nl/l/auto-s/bestelauto-s/","Marktplaats"))
    def test_listing(self): self.assertTrue(valid_url("https://www.marktplaats.nl/v/auto-s/bestelauto-s/m123456-test","Marktplaats"))
    def test_all_sources_present(self):
        self.assertIn("wijkopenautos",SOURCES)
        self.assertIn("TrucksNL",SOURCES)
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
        self.assertEqual(len(d["source_coverage"]),10)
        self.assertTrue(all(v["status"]=="unavailable" for v in d["source_coverage"].values()))
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
                return "<html><title>Peugeot Boxer L2H2 airco</title><body>Kenteken: V-360-SJ</body></html>","text/html"
            if url in SEED_PAGES["Marktplaats"]:
                return '<html><a href="'+target+'">Boxer L2H2 airco</a></html>',"text/html"
            raise OSError("unavailable")
        data=discover(fetcher=fetcher)
        self.assertEqual(len(data["candidates"]),1)
        self.assertEqual(data["candidates"][0]["plate"],"V-360-SJ")
        self.assertEqual(data["source_coverage"]["Marktplaats"]["direct_eligible_urls"],1)
    def test_only_relevant_target_vans_enter_dealer_queue(self):
        from discover_listings import relevant_link
        self.assertFalse(relevant_link("Audi A3","https://www.gaspedaal.nl/audi/a3","Gaspedaal"))
        self.assertFalse(relevant_link("Regional occasions","https://www.gaspedaal.nl/regio/occasions-alkmaar","Local dealers"))
        self.assertTrue(relevant_link("Peugeot Boxer L2H2","https://www.gaspedaal.nl/peugeot/boxer","Gaspedaal"))
    def test_category_markup_not_individual_listing(self):
        from discover_listings import extract
        page="<html><title>Peugeot Boxer occasions</title><p>Bekijk 50 Boxer aanbiedingen</p></html>"
        self.assertIsNone(extract("Peugeot Boxer","https://www.gaspedaal.nl/peugeot/boxer/occasion","Gaspedaal",page))
    def test_single_structured_vehicle_is_valid(self):
        from discover_listings import extract
        page='<html><title>Peugeot Boxer L2H2</title><script type="application/ld+json">{"@type":"Vehicle","name":"Peugeot Boxer L2H2","offers":{"@type":"Offer","price":"7000"}}</script></html>'
        self.assertIsNotNone(extract("Peugeot Boxer","https://www.gaspedaal.nl/peugeot/boxer/vehicle123","Gaspedaal",page))
    def test_multiple_product_objects_are_not_a_detail(self):
        from discover_listings import extract
        page='<html><title>Boxer list</title><script type="application/ld+json">[{"@type":"Product","name":"Boxer A","offers":{"price":7000}},{"@type":"Product","name":"Boxer B","offers":{"price":7500}}]</script></html>'
        self.assertIsNone(extract("Peugeot Boxer","https://www.gaspedaal.nl/peugeot/boxer/results","Gaspedaal",page))
    def test_gaspedaal_model_page_is_not_individual_listing(self):
        self.assertFalse(valid_url("https://www.gaspedaal.nl/peugeot/boxer","Gaspedaal"))
        self.assertFalse(valid_url("https://www.gaspedaal.nl/ford/transit","Gaspedaal"))
    def test_viabovag_model_search_not_individual_listing(self):
        self.assertFalse(valid_url("https://www.viabovag.nl/auto/merk-peugeot/model-boxer/occasion","viaBOVAG"))
    def test_targeted_seed_pages_exist(self):
        from discover_listings import SEED_PAGES
        self.assertIn("https://www.gaspedaal.nl/peugeot/boxer",SEED_PAGES["Gaspedaal"])
        self.assertIn("https://www.viabovag.nl/auto/merk-peugeot/model-boxer/occasion",SEED_PAGES["viaBOVAG"])
    def test_auxiliary_pages_rejected(self):
        self.assertFalse(valid_url("https://www.wijkopenautos.nl/auto-kopen/favorieten/","wijkopenautos"))
        self.assertFalse(valid_url("https://www.bedrijfsauto.nl/lease/calculator","Bedrijfsauto"))
        self.assertFalse(valid_url("https://www.gaspedaal.nl/regio/occasions-almere","Gaspedaal"))
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

if __name__=="__main__":unittest.main()
