import unittest
from camper_pipeline import evaluate, screen, report

class ScreeningTests(unittest.TestCase):
    def example(self):
        return {"name":"Synthetic fixture, not a real listing","listing_url":"https://example.com/van",
                "individual_listing_confirmed":True,"plate":"AB-123-C","plate_confirmed_from_listing":True,
                "checks":{key:True for key in ("high_roof","cab_ac","conversion_suitable","distance_within_100km","price_incl_vat_within_8000")}}
    def test_perfect_fixture_screening(self):
        self.assertTrue(screen(self.example())["qualified"])
    def test_unknown_ac_is_not_qualified(self):
        c=self.example(); c["checks"]["cab_ac"]=None
        self.assertFalse(screen(c)["qualified"])
    def test_unconfirmed_plate_is_not_qualified(self):
        c=self.example(); c["plate_confirmed_from_listing"]=False
        self.assertFalse(screen(c)["qualified"])
    def test_no_individual_listing_is_not_qualified(self):
        c=self.example(); c["individual_listing_confirmed"]=False
        self.assertFalse(screen(c)["qualified"])
    def test_rdws_failure_demotes(self):
        r=evaluate({"candidates":[self.example()]},lambda p:{"vehicle":{"status":"error"}})
        self.assertEqual(r["qualifiers"],0)
    def test_rdws_success_fixture(self):
        r=evaluate({"candidates":[self.example()]},lambda p:{"vehicle":{"status":"ok","records":[{"tellerstandoordeel":"Logisch"}]}})
        self.assertEqual(r["qualifiers"],1)
    def test_zero_candidates_honesty(self):
        self.assertIn("not proof",report(evaluate({"candidates":[]})))
if __name__=="__main__":unittest.main()
