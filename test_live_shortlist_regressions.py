"""Boundary regressions from the 124-advert live audit (2026-10-17)."""
from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import patch

from camper_pipeline import evaluate, report_priority, report_selection
from digest_details import details
from listing_identity import bind_evidence
from listing_evidence import enrich
from scoped_state import detail_facts
from suitability import variant_research
from test_scoped_state import URL, page, record
from vehicle_risks import mechanical_failure


class LiveShortlistRegressions(unittest.TestCase):
    def test_subtle_current_failure_is_rejected_but_history_and_negation_are_not(self):
        for text in ('Motor niet 100% goed lezen', 'Motor is niet 100 %', 'MOTOR NIET %100 GOED LEZEN', 'Heeft motorproblemen',
                     'Motor defect. Koppeling vervangen', 'Motor defect, koppeling vervangen', 'Het motorstoringslampje brandt'):
            self.assertIsNotNone(mechanical_failure(text), text)
        for text in ('Geen motorproblemen', 'Motor defect geweest, inmiddels gerepareerd',
                     'Motorproblemen verholpen', 'Motor defect, inmiddels vervangen',
                     'Garantie vervalt bij motorproblemen', 'Motorstoringslampje brandt niet'):
            self.assertIsNone(mechanical_failure(text), text)

    def test_contradictory_seller_vat_never_becomes_a_verified_gross_price(self):
        r = {**record(), 'description': 'Prijs ex btw € 4500,- incl btw'}
        scoped, _ = bind_evidence(page(r), URL)
        facts = enrich(scoped, lambda _: {}, lambda _: {})
        self.assertIsNone(facts['vat']['amount_incl_vat'])
        self.assertEqual(facts['vat']['source'], 'conflicting_same_listing_seller_price')
        self.assertNotIn('price_incl_vat_within_8000', facts['checks'])

    def test_separate_net_and_gross_prices_are_not_a_contradiction(self):
        for description in ('€ 4750 excl btw / € 5748 incl btw',
                            'Prijs excl btw € 4750; prijs incl btw € 5748'):
            facts = detail_facts(page({**record(), 'description':description}), URL)
            self.assertNotIn('seller_price_conflict', facts)

    def test_platform_inclusive_label_does_not_override_exclusive_seller_price(self):
        r = record()
        r['description'] = 'Verkoopprijs is exclusief btw'
        r['price']['vatLabel'] = 'Incl. BTW'
        r['prices']['public']['netPriceRaw'] = None
        scoped, _ = bind_evidence(page(r), URL)
        self.assertIsNone(enrich(scoped, lambda _: {}, lambda _: {})['vat']['amount_incl_vat'])

    def test_explicit_margin_advert_can_establish_consumer_price_without_net_field(self):
        r = record()
        r['description'] = 'Perfect rijdende auto. MARGE Goede airco MARGE'
        r['prices']['public'].update(netPriceRaw=None, netPrice=None, taxDeductible=False)
        facts = detail_facts(page(r), URL)
        self.assertTrue(facts['seller_reported_margin'])
        scoped, _ = bind_evidence(page(r), URL)
        self.assertEqual(enrich(scoped, lambda _: {}, lambda _: {})['vat']['amount_incl_vat'], 5748)
        r['description'] = 'Geen marge'
        self.assertNotIn('priceSpecification', detail_facts(page(r), URL))

    def test_seller_leakage_and_trade_terms_remain_attributed_cautions(self):
        from discover_listings import extract
        r = {**record(), 'description':'Oude lekkage sporen. Wij zijn gespecialiseerd in verkoop voor handel of export.'}
        with patch('discover_listings.enrich', return_value={'vat':{'amount_incl_vat':None,'basis':'unknown'}, 'checks':{},'distance_km':None,'location_coordinates':None}):
            c = extract('Boxer', URL, 'AutoScout24', page(r))
        self.assertEqual(len(c['advertised_cautions']), 2)
        self.assertIsNone(c['reported_mechanical_failure'])

    def test_variant_parsing_keeps_the_advertised_engine_and_gearbox_separate(self):
        for engine, gearbox, gears, expected in [('1.9 TDI', 'Handgeschakeld', 5, '5-speed manual'),
                ('2.5 TDI', 'Automatisch', 6, '6-speed automatic'), ('2.0 MultiJet', 'Handgeschakeld', None, None)]:
            c = {'variant_clues': [{'make':'Volkswagen' if 'TDI' in engine else 'Fiat',
                 'model':'Transporter' if 'TDI' in engine else 'Ducato', 'firstRegistrationDateRaw':'2008-10-01',
                 'modelVersionInput':engine, 'gears':gears, 'transmissionType':gearbox}]}
            research = variant_research(c, today=date(2026,10,17))
            self.assertEqual(research['variant']['engine'], engine)
            self.assertEqual(research['variant'].get('gearbox'), expected)
            self.assertFalse(research['exact_variant_identified'])
            self.assertNotIn('transporter-cfca-risk', [n['id'] for n in research['notes']])

    def test_own_engine_field_can_resolve_abbreviated_model_version(self):
        c = {'variant_clues':[{'make':'Ford','model':'Transit', 'modelVersionInput':'280M 2.2 TDC DC',
             'motorTypeName':'2.2 TDCi', 'firstRegistrationDateRaw':'2012-12-01',
             'transmissionType':'Handgeschakeld','gears':6}]}
        r = variant_research(c, today=date(2026,10,17))
        self.assertEqual(r['variant']['engine'], '2.2 TDCi')
        self.assertEqual([n['id'] for n in r['notes']], ['transit-mk7-22-family'])

    def test_missing_gears_and_generation_do_not_unlock_mechanical_scoring(self):
        c = {'variant_clues':[{'make':'Fiat', 'model':'Ducato', 'modelVersionInput':'2.0 MultiJet KH1',
             'firstRegistrationDateRaw':'2014-03-01', 'transmissionType':'Handgeschakeld'}]}
        r = variant_research(c, today=date(2026,10,17))
        self.assertTrue(r['notes'])
        self.assertFalse(r['exact_variant_identified'])
        self.assertIn('gearbox', r['missing_identity'])
        self.assertNotIn('body', r['variant'])

    def test_known_stock_review_is_explicit_and_never_changes_weekly_suppression(self):
        from test_camper_pipeline import ScreeningTests
        c = ScreeningTests().example()
        c['checks']['conversion_suitable'] = None
        data = evaluate({'candidates':[c]}, lambda plate: {'vehicle':{'status':'ok','records':[{'kenteken':plate}]}})
        data['results'][0]['history'] = {'show_in_digest':False, 'status':'unchanged'}
        self.assertEqual(report_selection(data)['potential'], [])
        data['report_context'] = 'development_review'
        self.assertEqual(len(report_selection(data)['potential']), 1)
        self.assertFalse(data['results'][0]['history']['show_in_digest'])
        from report_html import render_html
        self.assertIn('geen nieuwe advertenties', render_html(data))

    def test_rdw_warning_breaks_ties_and_poptop_question_cannot_disappear(self):
        base = {'candidate':{'checks':{'cab_ac':True}}, 'score':40,
                'search_assessment':{'matched':False}, 'rdw_risks':[]}
        risky = deepcopy(base)
        risky['rdw_risks'] = [{'code':'odometer_inconsistent','blocks_qualification':True}]
        self.assertGreater(report_priority(base), report_priority(risky))
        self.assertTrue(any('hefdak' in q for q in details(risky)['questions']))

    def test_own_model_title_and_description_body_are_used_without_borrowing(self):
        r = record()
        r['vehicle'].update(make='Volkswagen', model='Transporter', modelVersionInput='2.5 TDI DC')
        r['description'] = 'Volkswagen Transporter L1H1. Geen motorproblemen.'
        facts = detail_facts(page(r), URL)
        self.assertEqual(facts['seller_vehicle_identity']['advertisedBody'], 'L1H1')
        from discover_listings import extract
        with patch('discover_listings.enrich', return_value={'vat':{'amount_incl_vat':None,'basis':'unknown'}, 'checks':{},'distance_km':None,'location_coordinates':None}):
            c = extract('Peugeot Boxer', URL, 'AutoScout24', page(r))
        self.assertEqual(c['name'], 'Volkswagen Transporter 2.5 TDI DC')
        self.assertIsNone(c['reported_mechanical_failure'])
