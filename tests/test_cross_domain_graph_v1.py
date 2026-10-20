"""Neutral semantic coverage graph never creates false accepted outcomes."""
from __future__ import annotations
import copy
import unittest
from cite_refinery.cross_domain_graph import coverage_packet
from cite_refinery.cross_domain_roles import validate_roles
from cite_refinery.cross_domain_role_critic import validate_critique
from test_cross_domain_roles_v1 import MODULES,SOURCES,answer
from test_cross_domain_critic_v1 import review

DOMAIN={"id":"urban_heat","modules":MODULES}
def checked():
 return validate_critique(review(),validate_roles(answer(),"Were city heat alerts implemented?",MODULES,SOURCES),MODULES)

class CrossDomainGraphTests(unittest.TestCase):
 def test_neutral_modules_source_quote_and_unevaluated_program_gaps(self):
  pkt=coverage_packet(DOMAIN,checked())
  self.assertEqual(len(pkt["nodes"]),8)
  self.assertEqual(len(pkt["edges"]),5)
  self.assertEqual(sum(n["kind"]=="research_question" for n in pkt["nodes"]),3)
  self.assertTrue(all(n["layer"]=="neutral" for n in pkt["nodes"]))
  self.assertTrue(all(e["status"] in {"candidate","unresolved"} for e in pkt["edges"]))
  self.assertEqual({e["relation"] for e in pkt["edges"]},{"CONTEXT_FOR","REQUIRES"})
  self.assertEqual(pkt["conversion_metadata"]["accepted_program_outcomes"],0)
  text=" ".join(n["statement"] for n in pkt["nodes"])
  self.assertNotIn("free-roaming dog",text)
  self.assertIn("No documented real operation",text)
  self.assertIn("No directly reported program-outcome evaluation",text)
 def test_source_not_forced_into_wrong_perspective_or_duplicate_offtopic(self):
  pkt=coverage_packet(DOMAIN,checked())
  links=[e for e in pkt["edges"] if e["relation"]=="CONTEXT_FOR"]
  self.assertEqual(len(links),2)
  self.assertTrue(all(len(e["evidence_refs"])==1 for e in links))
 def test_reject_unreviewed_as_authority(self):
  v=validate_roles(answer(),"Heat?",MODULES,SOURCES)
  with self.assertRaises(ValueError):coverage_packet(DOMAIN,v)
  x=checked();x["coverage"].pop("HT-03")
  with self.assertRaisesRegex(ValueError,"Module coverage"):
   coverage_packet(DOMAIN,x)
if __name__=="__main__":unittest.main()
