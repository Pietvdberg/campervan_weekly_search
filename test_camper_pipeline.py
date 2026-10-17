import unittest
from camper_pipeline import evaluate, screen, report

class ScreeningTests(unittest.TestCase):
    def example(self):
        return {"name":"Synthetic fixture, not a real listing","listing_url":"https://example.com/van",
                "individual_listing_confirmed":True,"plate":"AB-123-C","plate_confirmed_from_listing":True,
                "independent_review":{"listing_url":"https://example.com/van","plate":"AB123C","reviewer":"Synthetic fixture only",
                    "observed_at":"2000-01-01T00:00:00+00:00","expires_at":"2100-01-01T00:00:00+00:00",
                    "checks":{key:{"confirmed":True,"method":"independent_inspection","source_url":"https://example.test/fictional-inspection"}
                              for key in ("cab_ac_working","available_for_sale","condition_acceptable")}},
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
        r=evaluate({"candidates":[self.example()]},lambda p:{"vehicle":{"status":"ok","records":[{"kenteken":"AB123C","tellerstandoordeel":"Logisch"}]}})
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
        self.assertIn("Local dealers: 1 examined",report(data))
    def test_dealer_audit_rows_preserve_unknowns(self):
        from camper_pipeline import dealer_audit_rows
        c=self.example()
        c.update({"source":"Local dealers","city_mentioned":"Roosendaal",
                  "price_advertised":"6500","price_incl_vat":None,"vat_basis":"unknown",
                  "distance_km":None})
        c["checks"]["distance_within_100km"]=None
        c["checks"]["price_incl_vat_within_8000"]=None
        c["checks"]["conversion_suitable"]=None
        evaluation=evaluate({"candidates":[c]},lambda _:{"vehicle":{"status":"ok","records":[{}]}})
        rows=dealer_audit_rows(evaluation)
        self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0]["verified_driving_distance_km"])
        self.assertIsNone(rows[0]["price_incl_vat"])
        self.assertIsNone(rows[0]["checks"]["conversion_suitable"])
        self.assertEqual(rows[0]["city_mentioned_not_verified"],"Roosendaal")
        self.assertFalse(evaluation["results"][0]["qualified"])
    def test_dealer_audit_rows_exclude_other_sources(self):
        from camper_pipeline import dealer_audit_rows
        self.assertEqual(dealer_audit_rows(evaluate({"candidates":[self.example()]})),[])
    def test_source_coverage_reason_visible_in_report(self):
        result=evaluate({"candidates":[],"source_coverage":{
            "AutoWereld":{"status":"no_verified_individual_pages",
                "coverage_note":"HTML fallback contained no vehicle advertisements."}}})
        output=report(result)
        self.assertIn("HTML fallback contained no vehicle advertisements",output)
        self.assertIn("not proof",output)
    def test_rss_only_leads_never_qualify(self):
        lead={"url":"https://www.autowereld.nl/peugeot/boxer/l2h2-43922209/details.html",
              "title":"Peugeot Boxer L2H2 Airco","description":"€ 7500, seller claim",
              "pub_date":"Fri, 16 Oct 2026 21:00:00 +0200"}
        result=evaluate({"candidates":[],"unverified_rss_leads":[lead]})
        self.assertEqual(result["qualifiers"],0)
        text=report(result)
        self.assertIn("UNVERIFIED leads",text)
        self.assertIn("Peugeot Boxer L2H2 Airco",text)
        self.assertIn("RSS-only",text)
    def test_zero_candidates_honesty(self):
        self.assertIn("not proof",report(evaluate({"candidates":[]})))

    def test_hard_failure_trumps_high_score(self):
        from camper_pipeline import candidate_state
        c=self.example()
        c["checks"]["price_incl_vat_within_8000"]=False
        item=screen(c)
        self.assertEqual(item["score"],80)
        self.assertEqual(candidate_state(item),"REJECTED")
        result=evaluate({"candidates":[c]},lambda _:self.fail("Should not call RDW for explicit budget rejection"))
        self.assertNotIn("Synthetic fixture",report(result))

    def test_tracking_query_and_confirmed_plate_duplicates_only_in_email(self):
        from camper_pipeline import unique_report_items
        a=self.example()
        b=self.example()
        a["listing_url"]="https://www.autotrack.nl/a/sample-123456?from_srp=true"
        b["listing_url"]="https://www.autotrack.nl/a/sample-123456"
        a["plate"]=b["plate"]=None
        a["plate_confirmed_from_listing"]=b["plate_confirmed_from_listing"]=False
        result=evaluate({"candidates":[a,b]})
        self.assertEqual(len(result["results"]),2)
        self.assertEqual(len(list(unique_report_items(result["results"]))),1)
        self.assertEqual(report(result).count("  Listing: https://www.autotrack.nl/a/sample-123456"),1)

    def test_rss_prefilter_removes_expensive_open_bed_and_damaged(self):
        from camper_pipeline import rss_shortlist
        def lead(title,price):
            return {"url":"https://www.autowereld.nl/renault/master/" +
                    str(len(title)) + "-" + str(price) + "/details.html",
                    "title":title,"description":"Vraagprijs : € "+price}
        sample=[
            lead("Renault Master L2H2 Airco","7.250"),
            lead("Renault Master L2H2 Airco open laadbak","6.000"),
            lead("Renault Master L3H2 Airco","19.950"),
            lead("Renault Master L1H1 Airco","3.000"),
            lead("Renault Master L2H2 motor niet goed","2.000"),
        ]
        chosen=rss_shortlist(sample)
        self.assertEqual(len(chosen),1)
        self.assertIn("Airco",chosen[0]["title"])

    def test_no_vat_inference_for_rss(self):
        from camper_pipeline import rss_shortlist
        lead={"url":"https://www.autowereld.nl/renault/master/l2h2-123/details.html",
              "title":"Renault Master L2H2 Airco","description":"Vraagprijs : € 7.900"}
        data=evaluate({"unverified_rss_leads":[lead]})
        self.assertEqual(data["qualifiers"],0)
        self.assertIn("VAT basis unknown",report(data))
        self.assertIn("RSS-only",report(data))

    def test_title_price_above_budget_does_not_appear_as_potential_match(self):
        c=self.example()
        c.update({"name":"Peugeot Boxer L2H2 Airco in Terneuzen voor € 19.999",
                  "price_incl_vat":None,"vat_basis":"unknown"})
        c["checks"].update({"conversion_suitable":None,"price_incl_vat_within_8000":None})
        data=evaluate({"candidates":[c]},lambda _:{"vehicle":{"status":"ok","records":[{}]}})
        self.assertEqual(len(data["results"]),1)
        self.assertNotIn("Peugeot Boxer L2H2 Airco in Terneuzen",report(data))

    def test_unknown_title_price_still_allowed_as_potential(self):
        c=self.example()
        c.update({"name":"Peugeot Boxer L2H2 Airco", "price_incl_vat":None})
        c["checks"].update({"conversion_suitable":None,"price_incl_vat_within_8000":None})
        data=evaluate({"candidates":[c]},lambda _:{"vehicle":{"status":"ok","records":[{}]}})
        self.assertIn("Peugeot Boxer L2H2 Airco",report(data))

    def test_audit_keeps_expensive_and_rejected_vehicles(self):
        c=self.example()
        c["checks"]["price_incl_vat_within_8000"]=False
        result=evaluate({"candidates":[c]})
        self.assertEqual(len(result["results"]),1)
        self.assertEqual(result["source_screening"]["Unknown"]["total"],1)
        self.assertIn("Explicitly rejected: 1",report(result))

if __name__=="__main__":unittest.main()
