"""Semantic source-role contracts, independent of source host or field."""
from __future__ import annotations
import copy
import unittest
from cite_refinery.cross_domain_roles import evidence_role_prompt,validate_roles

MODULES=[
 {"id":"HT-01","title":"Heat danger access","summary":"Resident heat exposure", "perspective":"practical"},
 {"id":"HT-02","title":"Heat health risk","summary":"Epidemiology and mortality","perspective":"academic"},
 {"id":"HT-03","title":"Heat measures","summary":"Alerts, centers, program outcomes","perspective":"program"},
]
SOURCES=[
 {"id":"OFFICIAL-heat","url":"https://www.who.int/news/heat-plan",
  "origin_type":"official_webpage_excerpt_unverified",
  "text":"National and local authorities should develop heat-health action plans including outreach and warning systems. Implementation and reductions in hospital admissions were not evaluated.",
  "source_scope":"Guidance, not an implementation audit"},
 {"id":"ACADEMIC-heat","url":"https://doi.org/10.1234/heat-study",
  "origin_type":"scholarly_abstract_lead",
  "text":"A cohort study of residents in a metropolitan city found high outdoor temperature was associated with excess emergency visits for dehydration.",
  "source_scope":"Academic observational cohort"},
 {"id":"ACADEMIC-unrelated","url":"https://doi.org/10.1234/dog-study",
  "origin_type":"scholarly_abstract_lead",
  "text":"This review examines free-roaming dog population estimates and the observed distribution of animal shelters.","source_scope":"Unrelated field"},
]
def answer():
 return {"assessments":[
 {"source_id":"OFFICIAL-heat","fit":"direct","role":"program_guidance_or_proposal",
  "module_ids":["HT-03"],"quote":"National and local authorities should develop heat-health action plans including outreach and warning systems.",
  "why":"Prescriptive heat planning guidance, not independently demonstrated implementation.",
  "limitations":"Does not measure center use, actual cooling access or heat-related hospital outcome reductions."},
 {"source_id":"ACADEMIC-heat","fit":"direct","role":"academic_finding",
  "module_ids":["HT-02"],"quote":"A cohort study of residents in a metropolitan city found high outdoor temperature was associated with excess emergency visits for dehydration.",
  "why":"Observational association from a metropolitan risk study, not a program intervention trial.",
  "limitations":"Association does not establish heat response program implementation or causal effect."},
 {"source_id":"ACADEMIC-unrelated","fit":"off_topic","role":"off_topic","module_ids":[],"quote":"",
  "why":"Dogs and animal shelters do not discuss human urban heat interventions.",
  "limitations":"This source cannot inform urban temperature exposure or heat action plans."}
 ]}

class CrossDomainRoleTests(unittest.TestCase):
 def test_prompt_drives_semantics_not_hostname(self):
  txt=evidence_role_prompt("Are heat plans actually evaluated?",MODULES,SOURCES)
  self.assertIn("WHO-hosted article",txt)
  self.assertIn("program",txt)
  self.assertIn("semantic",txt.lower())
 def test_prescriptive_who_site_is_not_mistaken_for_implemented_impact(self):
  v=validate_roles(answer(),"Are heat plans actually evaluated?",MODULES,SOURCES)
  self.assertEqual(len(v["results"]),3)
  self.assertEqual(v["coverage"]["HT-03"]["direct_roles"],["program_guidance_or_proposal"])
  self.assertFalse(v["coverage"]["HT-03"]["implementation_reported_in_source"])
  self.assertFalse(v["coverage"]["HT-03"]["measured_outcome_reported_in_source"])
  self.assertEqual(v["coverage"]["HT-01"]["source_coverage_status"],"gap_no_direct_source")
  self.assertEqual(v["coverage"]["HT-02"]["direct_roles"],["academic_finding"])
  self.assertEqual(v["authority"],"candidate_semantic_role_only")
 def test_ambiguous_or_fake_quote_rejected(self):
  x=answer()
  x["assessments"][0]["quote"]="The government completed every center and reduced deaths 99%"
  with self.assertRaisesRegex(ValueError,"verbatim"):validate_roles(x,"Heat?",MODULES,SOURCES)
  x=answer()
  x["assessments"][0]["role"]="measured_program_outcome"
  # Even a wrong confident role that uses a real quote needs a separate model
  # critic: structural checks do NOT prove semantic entailment.
  v=validate_roles(x,"Heat?",MODULES,SOURCES)
  self.assertTrue(v["coverage"]["HT-03"]["measured_outcome_reported_in_source"])
  self.assertEqual(v["authority"],"candidate_semantic_role_only")
 def test_off_topic_source_is_never_coverage(self):
  x=answer();x["assessments"][2]["module_ids"]=["HT-01"]
  with self.assertRaisesRegex(ValueError,"Off-topic"):validate_roles(x,"Heat?",MODULES,SOURCES)
  x=answer();x["assessments"][2]["source_id"]="ACADEMIC-heat"
  with self.assertRaisesRegex(ValueError,"duplicate"):validate_roles(x,"Heat?",MODULES,SOURCES)
 def test_missing_source_and_wrong_module(self):
  x=answer();x["assessments"].pop()
  with self.assertRaisesRegex(ValueError,"Unreviewed"):validate_roles(x,"Heat?",MODULES,SOURCES)
  x=answer();x["assessments"][0]["module_ids"]=["DG-01"]
  with self.assertRaisesRegex(ValueError,"unknown problem module"):validate_roles(x,"Heat?",MODULES,SOURCES)
 def test_role_restriction_to_program_module(self):
  x=answer();x["assessments"][0]["role"]="documented_implementation";x["assessments"][0]["module_ids"]=["HT-02"]
  with self.assertRaisesRegex(ValueError,"program-relevant"):validate_roles(x,"Heat?",MODULES,SOURCES)
if __name__=="__main__":unittest.main()
