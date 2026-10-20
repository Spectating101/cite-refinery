"""Independent expert review templates never masquerade as independent labels."""
import copy,json,unittest
from pathlib import Path
from cite_refinery.blind_review import blind_packet,reviewer_template,agreement

ROOT=Path(__file__).resolve().parents[1]/'research_materials/runtime_trials/fulltext_dog_20261020'

class IndependentReviewTests(unittest.TestCase):
 def setUp(self):
  d=json.loads((ROOT/'benchmark_cases.json').read_text())
  self.packet=blind_packet(d['cases'],d['source_doi'])
  self.expert=reviewer_template(self.packet)
  self.gold={x['id']:x['expected'] for x in d['cases']}
 def submission(self,name):
  x=copy.deepcopy(self.expert);x['reviewer_id']=name
  for c in x['cases']:
   c['label']=self.gold[c['id']]
   c['rationale']='My independent evidence assessment for this specific source statement.'
  return x
 def test_blinded_package_contains_no_expected_labels_or_gold_explanations(self):
  s=json.dumps(self.packet)
  self.assertNotIn('gold_reason',s)
  self.assertNotIn('"expected"',s)
  self.assertEqual(len(self.packet['cases']),21)
  self.assertEqual(self.expert['cases'][0]['label'],None)
 def test_agreement_is_computed_without_automatic_gold_acceptance(self):
  a=self.submission('reviewer-A');b=self.submission('reviewer-B')
  r=agreement(self.packet,a,b)
  self.assertEqual(r['agreements'],21)
  self.assertEqual(r['cohen_kappa'],1)
  self.assertFalse(r['accepted_gold'])
  b['cases'][0]['label']='unresolved'
  r=agreement(self.packet,a,b)
  self.assertEqual(r['disagreements'],1)
  self.assertLess(r['cohen_kappa'],1)
  self.assertEqual(r['disagreements_for_adjudication'][0]['id'],a['cases'][0]['id'])
 def test_no_false_independence_and_requires_complete_reasoned_submission(self):
  a=self.submission('reviewer-A');b=self.submission('reviewer-A')
  with self.assertRaises(ValueError):agreement(self.packet,a,b)
  b['reviewer_id']='reviewer-B';b['cases'].pop()
  with self.assertRaises(ValueError):agreement(self.packet,a,b)
  b=self.submission('reviewer-B');b['source_packet_digest']='fake'
  with self.assertRaises(ValueError):agreement(self.packet,a,b)

if __name__=='__main__':unittest.main()
