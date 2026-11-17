from copy import deepcopy
from tempfile import TemporaryDirectory
import unittest
from cite_refinery.legal_codex_record_access import search_plan,retention_lead,classify_observation,admission_assessment,semantic_packet

class RecordAccess018Tests(unittest.TestCase):
 def test_eight_targets_seven_private_one_general(self):
  p=search_plan();self.assertEqual(len(p['targets']),8)
  self.assertEqual(sum(t['scope']=='personal' for t in p['targets']),7)
  self.assertEqual(p['requests_submitted'],0);self.assertEqual(p['claimant_originals_obtained'],0)
 def test_no_claimant_or_representative_impersonation(self):
  for role in ('claimant','authorized_representative','verified=True'):
   with self.assertRaises(ValueError):search_plan(requester=role)
 def test_all_personal_targets_gate_access(self):
  for t in search_plan()['targets']:
   if t['scope']=='personal':self.assertEqual(t['access_gate'],'claimant_or_verified_representative_required')
 def test_general_policy_request_does_not_require_claimant_identity(self):
  t=next(t for t in search_plan()['targets'] if t['scope']=='nonpersonal')
  self.assertEqual(t['route'],'public_policy_woo');self.assertEqual(t['draft_status'],'UNSENT')
 def test_contact_history_two_locations_not_deleted_frontend(self):
  r=retention_lead(record_class='contact_history')
  self.assertIn('analytical_environment',r['candidate_search_locations'])
  self.assertIsNone(r['actual_record_exists']);self.assertIsNone(r['actual_deletion_date'])
 def test_interaction_policy_not_application_system_policy(self):
  r=retention_lead(record_class='benefit_application')
  self.assertIn('not specified',r['described_windows']['source_system'])
  self.assertIsNone(r['retained_until_guaranteed'])
 def test_historical_version_not_silently_current(self):
  with self.assertRaises(ValueError):retention_lead(record_class='contact_history',source_version='2026-11-18')
 def test_unknown_record_class_rejected(self):
  with self.assertRaises(ValueError):retention_lead(record_class='all_government_records')
 def test_frontend_absence_is_not_destruction(self):
  r=classify_observation(kind='not_found_in_frontend',record_id='contact_history',observed_at='2026-11-18')
  self.assertIn('analytical',r['next_evidence_step']);self.assertIsNone(r['record_destroyed'])
 def test_access_refusal_not_nonexistence(self):
  r=classify_observation(kind='access_refused',record_id='application_versions',observed_at='2026-11-18')
  self.assertIn('not_record_absence',r['next_evidence_step']);self.assertIsNone(r['record_destroyed'])
 def test_planned_logging_does_not_prove_deployment(self):
  r=classify_observation(kind='control_planned',record_id='consultation_audit',observed_at='2021-11-24')
  self.assertEqual(r['next_evidence_step'],'seek_dated_implementation_evidence')
 def test_access_timestamp_not_first_knowledge(self):
  r=classify_observation(kind='consultation_date_reported',record_id='consultation_audit',observed_at='2026-11-18')
  self.assertIsNone(r['actor_first_known_at']);self.assertFalse(r['operational_replay_admitted'])
 def test_zero_recovery_order_not_payment(self):
  r=classify_observation(kind='court_order_found',record_id='execution_ledger',observed_at='2026-03-25')
  self.assertIsNone(r['refund_paid']);self.assertEqual(r['next_evidence_step'],'seek_separate_execution_entries')
 def test_no_unsupported_actual_log_import(self):
  with self.assertRaises(ValueError):admission_assessment([{'kind':'original_operational_log','verified':True}])
 def test_access_right_is_not_possession(self):
  r=admission_assessment([{'kind':'access_right'},{'kind':'public_policy'}])
  self.assertFalse(r['admitted']);self.assertEqual(len(r['missing']),4)
 def test_changed_plan_cannot_forge_acquisition(self):
  r=search_plan();r['targets'][0]['original_obtained']=True
  with self.assertRaises(ValueError):semantic_packet(r)
 def test_no_credentials_or_claimant_identity_in_plan(self):
  import json
  p=search_plan();text=json.dumps(p).lower()
  self.assertFalse(p['claimant_identified']);self.assertNotIn('password',text)
  self.assertTrue(all(t['operational_first_known_at'] is None for t in p['targets']))
 def test_graph_contains_only_search_leads(self):
  g=semantic_packet(search_plan());self.assertEqual(len(g['nodes']),15)
  self.assertTrue(all(e['relation']=='SUGGESTS_RECORD_LOCATION_OR_ACCESS_ROUTE' and e['status']=='candidate' for e in g['edges']))
 def test_repeated_plan_does_not_mutate_catalogue(self):
  p=search_plan();p['targets'][0]['required'].append('injected')
  self.assertNotIn('injected',search_plan()['targets'][0]['required'])
 def test_native_cite_graph(self):
  from cite_refinery.app import CiteRefinery
  from cite_refinery.semantic import SemanticGraph
  packet=semantic_packet(search_plan())
  with TemporaryDirectory() as root:
   app=CiteRefinery(root);p=app.init_project('018 record-access leads','Unsent requests, no claimant originals')
   g=SemanticGraph(app.store);preview=g.preview_packet(p.id,packet)
   self.assertFalse(preview['authority_boundary_warnings'])
   r=g.ingest_packet(p.id,packet,expected_state_digest=preview['state_digest'])
   self.assertEqual(len(r['edge_ids']),len(packet['edges']))
   self.assertTrue(all(app.store.load()['semantic_edges'][x]['status']=='candidate' for x in r['edge_ids']))
if __name__=='__main__':unittest.main()
