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
    def test_dealer_evidence_counts_do_not_infer_missing_checks(self):
        van={"source":"Local dealers","name":"Van Mossel Crafter","listing_url":"https://www.vanmossel.nl/stock/example",
            "individual_listing_confirmed":True,"plate":None,"plate_confirmed_from_listing":False,
            "price_incl_vat":None,"distance_km":None,"vat_basis":"unknown",
            "checks":{"high_roof":True,"cab_ac":True,"conversion_suitable":None,
                "distance_within_100km":None,"price_incl_vat_within_8000":False}}
        data=evaluate({"candidates":[van]})
        stats=data["source_screening"]["Local dealers"]
        self.assertEqual(stats["checks"]["price_incl_vat_within_8000"]["failed"],1)
        self.assertEqual(stats["checks"]["distance_within_100km"]["unknown"],1)
        self.assertEqual(stats["verified_prices"],0)
        self.assertEqual(stats["verified_distances"],0)
        self.assertEqual(data["qualifiers"],0)
        self.assertIn("Local dealers: 1 candidates",report(data))
    def test_zero_candidates_honesty(self):
        self.assertIn("not proof",report(evaluate({"candidates":[]})))
if __name__=="__main__":unittest.main()
