"""019 outcome scope, citation normalization and real-source regression tests.
No counts below are a legal-effectiveness or model-accuracy estimate.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from cite_refinery.legal_codex_access_outcomes import (
 build,discover_references,digest,load_sources,admission,semantic_packet)

class LiteralCitation019Tests(unittest.TestCase):
 def test_unicode_case_number_without_semantic_inference(self):
  hits=discover_references([{'id':'p1','text':'HvJ C\u2011579/21, ECLI:EU:C:2023:501'}])
  self.assertEqual([h['reference'] for h in hits],['C-579/21','ECLI:EU:C:2023:501'])
  self.assertTrue(all(not h['legal_applicability_inferred'] for h in hits))
 def test_no_automatic_correction_of_truncated_ecli(self):
  hits=discover_references([{'id':'p1','text':'ECLI:EU:C:2023:50; ECLI:EU:C:2023:501'}])
  self.assertEqual([h['reference'] for h in hits],['ECLI:EU:C:2023:50','ECLI:EU:C:2023:501'])
 def test_article_number_not_a_case_citation(self):
  self.assertEqual(discover_references([{'id':'p1','text':'Artikel 15 lid 1 AVG'}]),[])
 def test_log_replay_is_not_admitted_from_judicial_receipt(self):
  out=admission({'schema':'legal_codex.access_outcomes_019.v1'})
  self.assertFalse(out['operational_replay_allowed']);self.assertEqual(len(out['missing']),4)

@unittest.skipUnless(os.environ.get('LEGAL_CODEX_019_EVIDENCE'),'Actual official sources required in dedicated 019 job')
class ActualAccessOutcomes019Tests(unittest.TestCase):
 def setUp(self):self.folder=Path(os.environ['LEGAL_CODEX_019_EVIDENCE'])
 def report(self):return build(self.folder)
 def obs(self,sid,dimension):return [r for r in self.report()['observations'] if r['source_id']==sid and r['dimension']==dimension]
 def test_three_court_cases_plus_separate_institutional_source(self):
  r=self.report();self.assertEqual(r['curated_judgments'],3);self.assertEqual(r['captured_core_sources'],4)
  self.assertEqual(len(r['observations']),13);self.assertEqual(r['private_medical_or_tax_logs_obtained'],0)
 def test_recipient_acknowledgement_different_from_our_custody(self):
  rows=self.obs('hospital_2026','delivery')
  self.assertEqual(len(rows),2)
  self.assertTrue(all(r['evidence_role']=='court_records_claimant_confirmation' for r in rows))
  self.assertTrue(all(not r['claimant_records_acquired'] for r in rows))
 def test_log_receipt_and_intelligibility_order_coexist(self):
  self.assertTrue(self.obs('hospital_2026','delivery'))
  row=self.obs('hospital_2026','intelligibility')[0]
  self.assertEqual(row['outcome_status'],'specific_data_and_purpose_explanation_ordered')
  self.assertEqual(row['evidence_role'],'operative_order')
  self.assertFalse(row['subsequent_compliance_verified'])
 def test_2026_decision_and_publication_are_distinct(self):
  r=self.obs('hospital_2026','access') or self.obs('hospital_2026','delivery')
  self.assertEqual(r[0]['source_date'],'2026-09-30')
  self.assertIn('2026-10-15',r[0]['publication_values'])
 def test_staff_detail_order_is_privacy_qualified_not_blanket_names(self):
  row=self.obs('hospital_2026','staff_identity')[0]
  self.assertEqual(row['outcome_status'],'specification_subject_to_privacy_ordered')
  self.assertIn('privacy',row['outcome_status'])
 def test_ministry_names_requirement_reversed_without_global_access_denial(self):
  statuses={r['outcome_status'] for r in self.obs('staff_identity_2025','staff_identity')}
  self.assertEqual(statuses,{'employee_names_not_necessary_in_this_case','lower_identity_disclosure_requirement_reversed'})
 def test_prior_log_absence_does_not_infer_intentional_destruction(self):
  row=self.obs('staff_identity_2025','traceability')[0]
  self.assertEqual(row['outcome_status'],'earlier_access_not_reconstructable')
  self.assertIn('does not prove intentional deletion',row['label'])
 def test_opposite_conditional_penalty_outcomes_not_confused(self):
  self.assertEqual(self.obs('hospital_2024','enforcement')[0]['outcome_status'],'conditional_penalty_ordered')
  self.assertEqual(self.obs('hospital_2026','enforcement')[0]['outcome_status'],'requested_penalty_not_imposed')
 def test_new_institutional_advice_not_retroactive_deployment_proof(self):
  row=self.obs('contact_center_2026','implementation')[0]
  self.assertEqual(row['source_date_kind'],'publication_date');self.assertEqual(row['source_date'],'2026-06-01')
  self.assertIn('not certify any 2023 logging',row['label'])
 def test_real_2026_to_2024_citations_extracted_without_annotation(self):
  links=self.report()['cross_case_citations']
  self.assertTrue(any(r['from_source']=='hospital_2026' and r['to_source']=='hospital_2024' for r in links))
  self.assertTrue(all(not r['same_proceeding_proven'] and not r['causal_effect_proven'] for r in links))
 def test_2023_rule_citations_are_literal_not_imagined(self):
  refs=self.report()['discovered_reference_mentions']
  self.assertTrue(any(r['source_id']=='hospital_2026' and r['reference']=='C-579/21' for r in refs))
  self.assertTrue(any(r['source_id']=='staff_identity_2025' and r['reference']=='C-579/21' for r in refs))
 def test_apparent_source_reference_shortening_is_preserved(self):
  refs=self.report()['unresolved_literal_references']
  self.assertEqual(len(refs),2)
  self.assertTrue(all(r['reference']=='ECLI:EU:C:2023:50' for r in refs))
 def test_all_original_block_hashes_match(self):
  for r in self.report()['observations']:
   self.assertEqual(digest(r['source_quote'].encode()),r['paragraph_sha256'])
   self.assertFalse(r['analyst_interpretation_independently_reviewed'])
 def test_failed_finnish_lead_never_counted_as_captured_core(self):
  r=self.report();self.assertNotIn('finnish_tax_2026',{x['source_id'] for x in r['observations']})
  row=next(x for x in r['source_status'] if x['source_id']=='finnish_tax_2026')
  self.assertEqual(row['status'],'failed')
 def test_stale_or_promoted_execution_refused_by_graph(self):
  r=self.report();r['subsequent_order_execution_verified']=True
  with self.assertRaisesRegex(ValueError,'modified'):semantic_packet(self.folder,r)
 def test_original_hash_or_extraction_modification_refused(self):
  import shutil
  with TemporaryDirectory() as temp:
   root=Path(temp);shutil.copytree(self.folder,root/'copy')
   path=root/'copy'/'hospital_2026.json';obj=json.loads(path.read_text())
   obj['blocks'][56]['text']='False claim of completed compliance'
   path.write_text(json.dumps(obj))
   with self.assertRaisesRegex(ValueError,'extraction differs'):load_sources(root/'copy')
 def test_native_cite_graph_ingests_scoped_not_causal_edges(self):
  from cite_refinery.app import CiteRefinery
  from cite_refinery.semantic import SemanticGraph
  packet=semantic_packet(self.folder,self.report())
  self.assertEqual(len(packet['nodes']),17);self.assertEqual(len(packet['edges']),14)
  self.assertTrue(all(e['status']=='candidate' for e in packet['edges']))
  self.assertFalse(any(e['relation'] in {'CAUSES','PREVENTED','PAID','LAW_APPLIES'} for e in packet['edges']))
  with TemporaryDirectory() as work:
   app=CiteRefinery(work);p=app.init_project('019 scoped access outcomes','Public judicial accounts, no private dossiers')
   g=SemanticGraph(app.store);preview=g.preview_packet(p.id,packet)
   self.assertFalse(preview['authority_boundary_warnings'])
   receipt=g.ingest_packet(p.id,packet,expected_state_digest=preview['state_digest'])
   self.assertEqual(len(receipt['edge_ids']),14)

if __name__=='__main__':unittest.main()
