"""Second role-critic pass cannot falsely upgrade evidence status."""
from __future__ import annotations
from copy import deepcopy
import unittest
from cite_refinery.cross_domain_roles import validate_roles
from cite_refinery.cross_domain_role_critic import critique_prompt,validate_critique
from test_cross_domain_roles_v1 import MODULES,SOURCES,answer

def base():
 return validate_roles(answer(),"Are heat plans actually evaluated?",MODULES,SOURCES)
def review():
 return {"assessments":[
  {"source_id":"OFFICIAL-heat","decision":"affirm",
   "safe_role":"program_guidance_or_proposal",
   "reason":"Original text recommends actions, with no observed implementation outcome."},
  {"source_id":"ACADEMIC-heat","decision":"affirm",
   "safe_role":"academic_finding",
   "reason":"This is a reported observational cohort finding, not intervention evidence."},
  {"source_id":"ACADEMIC-unrelated","decision":"affirm",
   "safe_role":"off_topic",
   "reason":"The text concerns dogs and cannot support human heat intervention coverage."},
 ]}

class RoleCriticTests(unittest.TestCase):
 def test_valid_second_review_preserves_coverage(self):
  result=validate_critique(review(),base(),MODULES)
  self.assertFalse(result["coverage"]["HT-03"]["implementation_reported_in_source"])
  self.assertEqual(result["critic_independence"],"separate_call_same_model_family_not_independent_validation")
  self.assertIn("separate",result["critic_independence"])
 def test_critic_downgrades_false_impact_without_promoting(self):
  b=base()
  b["results"][0]["role"]="measured_program_outcome"
  proposed=review()
  proposed["assessments"][0]["decision"]="downgrade"
  proposed["assessments"][0]["safe_role"]="program_guidance_or_proposal"
  result=validate_critique(proposed,b,MODULES)
  self.assertEqual(result["results"][0]["pre_critique_role"],"measured_program_outcome")
  self.assertEqual(result["results"][0]["role"],"program_guidance_or_proposal")
  self.assertFalse(result["coverage"]["HT-03"]["measured_outcome_reported_in_source"])
 def test_upgrade_forbidden(self):
  x=review()
  x["assessments"][0]["decision"]="downgrade"
  x["assessments"][0]["safe_role"]="documented_implementation"
  with self.assertRaisesRegex(ValueError,"upgrade"):validate_critique(x,base(),MODULES)
 def test_unreviewed_or_missing_rationale_forbidden(self):
  x=review();x["assessments"].pop()
  with self.assertRaisesRegex(ValueError,"Incomplete"):validate_critique(x,base(),MODULES)
  x=review();x["assessments"][0]["reason"]="yes"
  with self.assertRaisesRegex(ValueError,"rationale"):validate_critique(x,base(),MODULES)
 def test_role_interpretation_prompt_uses_full_source_contents(self):
  prompt=critique_prompt(base(),SOURCES)
  self.assertIn("not automatically",prompt.lower())
  self.assertIn("develop heat-health action plans",prompt)
  self.assertIn("independently",prompt.lower())
if __name__=="__main__":unittest.main()
