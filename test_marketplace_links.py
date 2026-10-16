import unittest
from marketplace_links import extract, source_detail

SCOUT="https://www.autoscout24.nl/aanbod/peugeot-boxer-diesel-wit-76517dc4-5b39-4637-af35-b89dca80173e"
TRUCK="https://www.bedrijfsauto.nl/peugeot-boxer-111721152"
WORLD="https://www.autowereld.nl/peugeot/boxer/330-l2h2-43911117/details.html"

class ExtractionTests(unittest.TestCase):
    def test_scout_response_structure_diagnostics(self):
        from marketplace_links import diagnostics
        markup='<a href="/aanbod/peugeot-boxer-diesel-wit-76517dc4-5b39-4637-af35-b89dca80173e">Boxer</a>'
        d=diagnostics(markup,"https://www.autoscout24.nl/lst/peugeot/boxer","AutoScout24")
        self.assertEqual(d["first_party_aanbod_anchors"],1)
        self.assertEqual(d["uuid_occurrences"],1)
    def test_scout_embedded_url_followed_by_json_suffix(self):
        from marketplace_links import extract
        data='{"payload":"\/aanbod\/peugeot-boxer-diesel-wit-76517dc4-5b39-4637-af35-b89dca80173e","extra":"value"}'
        self.assertEqual(extract(data,"https://www.autoscout24.nl/lst/peugeot/boxer","AutoScout24")[0][1],SCOUT)
    def test_scout_embedded_url_unicode_escaped_delimiters(self):
        from marketplace_links import extract
        data=r'{"url":"\u002Faanbod\u002Fpeugeot-boxer-diesel-wit-76517dc4\u002D5b39\u002D4637\u002Daf35\u002Db89dca80173e"}'
        self.assertEqual(extract(data,"https://www.autoscout24.nl/lst/peugeot/boxer","AutoScout24")[0][1],SCOUT)
    def test_scout_diagnostics_show_path_shape(self):
        from marketplace_links import diagnostics
        data='<script>{"url":"/aanbod/peugeot-boxer-diesel-wit-76517dc4-5b39-4637-af35-b89dca80173e"}</script>'
        self.assertIn("/aanbod/peugeot-boxer",diagnostics(data,"https://www.autoscout24.nl/lst/peugeot/boxer","AutoScout24")["offer_path_samples"][0])
    def test_scout_anchor(self):
        markup='<a href="'+SCOUT+'">Peugeot Boxer L2H2</a>'
        self.assertEqual(len(extract(markup,"https://www.autoscout24.nl/lst/peugeot/boxer","AutoScout24")),1)
    def test_bedrijfsauto_relative(self):
        markup='<a href="/peugeot-boxer-111721152">Boxer L2H2</a>'
        self.assertEqual(extract(markup,"https://www.bedrijfsauto.nl/","Bedrijfsauto")[0][1],TRUCK)
    def test_autowereld_details(self):
        markup='<a href="'+WORLD+'">Peugeot Boxer</a>'
        self.assertEqual(extract(markup,"https://www.autowereld.nl/","AutoWereld")[0][1],WORLD)
    def test_category_rejected(self):
        self.assertFalse(source_detail("https://www.autoscout24.nl/lst/peugeot/boxer","AutoScout24"))
        self.assertFalse(source_detail("https://www.bedrijfsauto.nl/","Bedrijfsauto"))
    def test_host_spoof_rejected(self):
        bad=SCOUT.replace("autoscout24.nl","autoscout24.nl.attacker.example")
        self.assertFalse(source_detail(bad,"AutoScout24"))
    def test_irrelevant_car(self):
        markup='<a href="https://www.bedrijfsauto.nl/volkswagen-polo-111721152">VW Polo</a>'
        self.assertEqual(extract(markup,"https://www.bedrijfsauto.nl/","Bedrijfsauto"),[])
if __name__=="__main__":
    unittest.main()
