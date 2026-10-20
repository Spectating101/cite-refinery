"""Proof that official publisher reputation does not override topic relevance."""
from __future__ import annotations
from tempfile import TemporaryDirectory
import unittest
from cite_refinery.investigation_controller import InvestigationController
from test_investigation_controller_v1 import MODULES,SOURCES

class EvidenceRepairRelevanceTests(unittest.TestCase):
    def test_unrelated_official_source_is_quarantined_before_reasoning(self):
        with TemporaryDirectory() as root:
            def must_not_reason(prompt):
                raise AssertionError("No LLM reasoning with an off-topic official source")
            ctrl=InvestigationController(root,reasoner=must_not_reason)
            s=ctrl.start("Which dog rabies intervention results match community dog abundance surveys?",MODULES)
            s["lineage"]={"source_audit_digest":"frozen-valid-article-hash"}
            bad={"id":"OFFICIAL-WASTE","url":"https://www.who.int/news/waste",
                 "title":"Global waste management and recycling",
                 "text":"The global environmental waste sector faces major health risks from poor recycling practices.",
                 "origin_type":"official_webpage_excerpt_unverified"}
            academic=dict(SOURCES["EPMC-123456789012"])
            s["rounds"]=[{"number":1,"focus":"Dog rabies intervention and dog population abundance measurement",
                         "plan":{"focus":"Dog population measurement","queries":[]},
                         "sources":[academic,bad],"source_attempts":1,
                         "source_failures":[],"state":"sources_retrieved"}]
            s["stage"]="reason"
            ctrl.save(s)
            after=ctrl.step(s["id"])
            self.assertEqual(after["stage"],"needs_sources")
            self.assertEqual(len(after["rounds"][0]["sources"]),1)
            self.assertEqual(after["rounds"][0]["sources"][0]["id"],academic["id"])
            self.assertEqual(after["rounds"][0]["excluded_off_topic_sources"][0]["source_id"],bad["id"])
            self.assertEqual(ctrl.load(s["id"])["stage"],"needs_sources")
            self.assertEqual(len(ctrl.app.store.load()["semantic_edges"]),0)

if __name__=="__main__":unittest.main()
