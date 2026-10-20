"""Semantic gap recovery must not invent evidence or erase original scope."""
from __future__ import annotations
from unittest.mock import patch
import unittest
from cite_refinery.cross_domain_recovery import recovery_prompt,retrieve_recovery
from cite_refinery.cross_domain_roles import validate_roles
from test_cross_domain_roles_v1 import MODULES,SOURCES,answer

def plan():
 return {
    "focus":"City heat action plans for vulnerable residents: implemented outreach versus evaluated morbidity",
    "reason":"Program guidance is not the same as observed implementation with measured local outcomes.",
    "hypotheses":["Published health action plan guidance may not document actual program delivery."],
    "queries":[{"lane":"academic","query":"heat action plan evaluation mortality city"},
               {"lane":"official","query":"heat health action plans implementation evidence"}],
 }

class CrossDomainRecoveryTests(unittest.TestCase):
 def test_prompt_prioritizes_evidence_gaps_not_new_citation_fabrication(self):
  roles=validate_roles(answer(),"Were heat plans implemented?",MODULES,SOURCES)
  prompt=recovery_prompt("Were heat plans implemented?",MODULES,roles,plan())
  self.assertIn("source",prompt.lower())
  self.assertIn("HT-01",prompt)
  self.assertIn("operational",prompt)
  self.assertIn("Do not provide URLs",prompt)
 def test_source_dedup_and_unverified_state(self):
  fresh=[{"id":"NEWSRC","url":"https://www.who.int/new-heat-document",
          "text":"WHO heat guidance for cities etc.","origin_type":"official_webpage_excerpt_unverified"}]
  repeats=[SOURCES[0],fresh[0]]
  with patch("cite_refinery.cross_domain_recovery.collect_sources",
             return_value={"sources":repeats,"failures":[],"searches_attempted":2}):
   recovered=retrieve_recovery(plan(),SOURCES)
  self.assertEqual(len(recovered["sources"]),1)
  self.assertEqual(recovered["sources"][0]["id"],"NEWSRC")
  self.assertIn("Unreviewed",recovered["note"])
 def test_invalid_queries_fail_validation(self):
  broken=plan();broken["queries"][1]["lane"]="something"
  with self.assertRaisesRegex(ValueError,"lane"):
   retrieve_recovery(broken,SOURCES)

if __name__=="__main__":unittest.main()
