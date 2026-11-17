"""017 source-backed chronology and adversarial evidence-tier checks.

Live-source tests require actual captured snapshots, not invented court text.
The dedicated workflow sets the evidence directory and requires native imports.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from cite_refinery.legal_codex_source_timeline_catalogue import make_fixture
from cite_refinery.legal_codex_source_timeline import (
    as_of,build,digest,load_sources,read_xml,semantic_packet,to_operational_replay,validate)

class EvidenceBoundary017Tests(unittest.TestCase):
    def test_operational_conversion_never_uses_boolean_override(self):
        for flags in ({},{'verified':True},{'allow_real_case':True}):
            with self.assertRaisesRegex(ValueError,'Admission refused'):
                to_operational_replay({'mode':'judicial_reconstruction'},**flags)
    def test_dtd_rejected(self):
        raw=b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY y "abc">]><x>&y;</x>'
        with self.assertRaisesRegex(ValueError,'entity'):
            read_xml(raw,'ECLI:NL:RVS:2026:1753')
    def test_source_size_limit(self):
        with self.assertRaisesRegex(ValueError,'byte budget'):
            read_xml(b'x'*(1024*1024+1),'ECLI:NL:RVS:2026:1753')
    def test_016_does_not_accept_judgment_fixture(self):
        from cite_refinery.legal_codex_control_replay import replay
        with self.assertRaises(ValueError):
            replay({'schema':'legal_codex.judicial_timeline.v1','mode':'judicial_reconstruction'})

@unittest.skipUnless(os.environ.get('LEGAL_CODEX_017_EVIDENCE'),'Actual court snapshots supplied in dedicated live-source CI')
class CapturedJudicialTimeline017Tests(unittest.TestCase):
    def setUp(self):
        self.folder=Path(os.environ['LEGAL_CODEX_017_EVIDENCE'])
        self.sources=load_sources(self.folder)
        self.b=make_fixture(self.sources)
    def row(self,ident):
        return next(x for x in self.b['facts'] if x['id']==ident)
    def test_real_sources_and_twenty_four_bound_statements(self):
        r=build(self.b,self.sources)
        self.assertEqual(r['source_count'],3);self.assertEqual(r['case_count'],2)
        self.assertEqual(r['fact_count'],24);self.assertEqual(r['original_operational_logs_obtained'],0)
        self.assertFalse(r['operational_replay_admission']['allowed'])
        self.assertFalse(r['observed_prevention_established'])
    def test_direct_case_join_not_anonymized_names(self):
        r=build(self.b,self.sources)
        self.assertEqual(r['official_same_case_link']['basis'],'reciprocal_official_ECLI_metadata')
        self.assertEqual(r['official_same_case_link']['from'],'ECLI:NL:RBGEL:2025:1418')
        self.assertEqual(r['official_same_case_link']['to'],'ECLI:NL:RVS:2026:1753')
    def test_missing_first_known_remains_unknown(self):
        r=build(self.b,self.sources)
        self.assertTrue(all(x['first_known_at'] is None for x in r['facts']))
        point=as_of(r,'benefits_2023','2024-03-18')
        self.assertIsNone(point['operational_evidence_available_at_checkpoint'])
        self.assertFalse(point['may_drive_016_operational_replay'])
        self.assertIn('objection_rejected',point['retrospectively_dated_events_by_checkpoint'])
        self.assertIn('appeal_missing_agency_form',point['findings_reported_only_by_later_judgments'])
    def test_future_absence_finding_not_backdated(self):
        self.row('appeal_missing_agency_form')['day']='2024-01-05'
        with self.assertRaisesRegex(ValueError,'backdated'):build(self.b,self.sources)
    def test_exact_date_cannot_be_shifted_while_token_stays(self):
        self.row('assisted_application')['day']='2023-04-13'
        with self.assertRaisesRegex(ValueError,'disagree'):build(self.b,self.sources)
    def test_false_actor_knowledge_rejected(self):
        self.row('original_recovery')['first_known_at']='2024-01-05T09:00:00Z'
        with self.assertRaisesRegex(ValueError,'first-known'):build(self.b,self.sources)
    def test_party_claim_does_not_become_judicial_finding(self):
        self.row('phone_contact_claim')['role']='court_finding'
        with self.assertRaisesRegex(ValueError,'cannot be promoted'):build(self.b,self.sources)
    def test_case_mix_rejected(self):
        self.row('comparator_recovery_upheld')['case_id']='benefits_2023'
        with self.assertRaisesRegex(ValueError,'cross-case'):build(self.b,self.sources)
    def test_cannot_drop_inconvenient_hearing_result(self):
        self.b['facts']=[x for x in self.b['facts'] if x['id']!='appeal_hearing_ground_rejected']
        with self.assertRaisesRegex(ValueError,'must not be omitted'):build(self.b,self.sources)
    def test_hearing_and_waiver_are_different_grounds(self):
        r=build(self.b,self.sources);grounds={x['issue']:x for x in r['ground_distinctions']}
        self.assertEqual(grounds['hearing_duty']['finding'],'breach_found_but_no_separate_appellate_relief')
        self.assertEqual(grounds['agency_record_uncertainty_and_proportionality']['finding'],'case_specific_recovery_waiver')
        self.assertEqual(grounds['benefit_reassessment']['finding'],'otherwise_upheld')
    def test_waiver_is_not_cash_paid(self):
        self.row('appeal_zero_recovery')['money_effect']='cash_refunded'
        with self.assertRaisesRegex(ValueError,'cash refund'):build(self.b,self.sources)
    def test_other_genuine_paragraph_cannot_replace_outcome(self):
        f=self.row('appeal_zero_recovery');f['paragraph_id']='p0035'
        f['paragraph_sha256']=digest(self.sources['appeal_2026']['paragraphs']['p0035'].encode())
        with self.assertRaisesRegex(ValueError,'anchor changed'):build(self.b,self.sources)
    def test_captured_text_cannot_be_rewritten(self):
        self.sources['appeal_2026']['paragraphs']['p0057']='The court ordered a cash refund.'
        with self.assertRaisesRegex(ValueError,'differs from original'):build(self.b,self.sources)
    def test_metadata_cannot_reclassify_court_date(self):
        self.sources['appeal_2026']['decided_on']='2024-01-05'
        with self.assertRaisesRegex(ValueError,'metadata mismatch'):build(self.b,self.sources)
    def test_receipt_flags_without_source_bytes_are_not_enough(self):
        del self.sources['appeal_2026']['_raw_bytes']
        with self.assertRaisesRegex(ValueError,'source bytes required'):build(self.b,self.sources)
    def test_stale_graph_refused(self):
        r=build(self.b,self.sources);r['observed_prevention_established']=True
        with self.assertRaisesRegex(ValueError,'fabricated'):semantic_packet(self.b,self.sources,r)
    def test_native_graph_and_no_causal_or_payment_edges(self):
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        r=build(self.b,self.sources);packet=semantic_packet(self.b,self.sources,r)
        self.assertEqual(len(packet['edges']),25)
        self.assertFalse(any(e['relation'] in {'CAUSES','PREVENTED','PAID'} for e in packet['edges']))
        with TemporaryDirectory() as root:
            app=CiteRefinery(root);p=app.init_project('Judicial chronology','Not operational decision logs')
            g=SemanticGraph(app.store);v=g.preview_packet(p.id,packet)
            self.assertFalse(v['authority_boundary_warnings'])
            receipt=g.ingest_packet(p.id,packet,expected_state_digest=v['state_digest'])
            self.assertEqual(len(receipt['edge_ids']),25)
            self.assertTrue(all(app.store.load()['semantic_edges'][e]['status']=='candidate' for e in receipt['edge_ids']))
    def test_all_anchors_exactly_reextract_from_sources(self):
        r=build(self.b,self.sources)
        for f in r['facts']:
            self.assertEqual(digest(f['source_quote'].encode()),f['paragraph_sha256'])
            self.assertFalse(f['is_operational_log_entry'])
    def test_future_event_after_judgment_rejected(self):
        self.row('assisted_application')['day']='2028-04-12'
        with self.assertRaisesRegex(ValueError,'after cited'):build(self.b,self.sources)
    def test_timestamp_fabrication_by_mode_switch_rejected(self):
        self.b['mode']='operational_logs'
        with self.assertRaisesRegex(ValueError,'unsupported timeline'):build(self.b,self.sources)
    def test_role_and_effect_scope_preserved_in_output(self):
        r=build(self.b,self.sources);byid={f['id']:f for f in r['facts']}
        self.assertEqual(byid['phone_contact_claim']['role'],'party_submission')
        self.assertEqual(byid['appeal_zero_recovery']['money_effect'],'court_ordered_zero_recovery')
        self.assertTrue(r['court_waiver_is_not_cash_refund'])
    def test_unknown_case_cannot_be_queried(self):
        with self.assertRaisesRegex(ValueError,'wrong evidence'):
            as_of(build(self.b,self.sources),'invented-case','2024-01-05')

if __name__=='__main__':unittest.main()
