"""Contradiction-led challenge tests against real Cite-Refinery persistence."""
import unittest
from tempfile import TemporaryDirectory
from copy import deepcopy
from cite_refinery.investigation_controller import InvestigationController
from cite_refinery.investigation_adjudication import ChallengeController,validate_adjudication,source_topic_fit
from test_investigation_controller_v1 import StubReasoner,MODULES,SOURCES

NEW_A={"id":"EPMC-NOVEL","url":"https://doi.org/10.1/novel-method",
  "text":"In repeat dog surveys, visibility differences create inconsistent counts even where true population size changes little. A careful observer can detect a different apparent trend.",
  "source_scope":"Separate scholarly abstract lead, not full empirical replication",
  "origin_type":"scholarly_abstract_lead"}
NEW_O={"id":"OFFICIAL-NOVEL","url":"https://www.woah.org/en/document/monitoring-dogs",
  "text":"Population monitoring requires stable repeated routes and demographic turnover observations. Programme reports must distinguish a sterilization count from the actual dog population.",
  "source_scope":"Institutional recommendations, not local data",
  "origin_type":"official_webpage_excerpt_unverified"}

class Judge:
    def __init__(self,bad=False,fail=False):self.prompts=[];self.bad=bad;self.fail=fail
    def __call__(self,prompt):
        self.prompts.append(prompt)
        if self.fail:
            self.fail=False;raise TimeoutError("provider unavailable")
        if "FALSIFICATION-ORIENTED RESEARCH PLANNER" in prompt:
            return {"claim_ids":["R1:P1"],
                "reason":"Observed canine abundance is very sensitive to different detection and sampling assumptions.",
                "counter_hypotheses":["Adjusted animal visibility may change estimated absolute dog abundance."],
                "queries":[{"lane":"academic","query":"adjusted canine mark resight population surveys"},
                           {"lane":"official","query":"official dog population monitoring evaluation"}]}
        if "NEW-SOURCE CONTRADICTION ADJUDICATOR" in prompt:
            quote=("fake evidence shows 50% population reduction" if self.bad else
                   "visibility differences create inconsistent counts even where true population size changes little")
            return {"assessments":[{"claim_id":"R1:P1","verdict":"scope_qualified",
                "rationale":"Method-specific interpretation supports detection heterogeneity without establishing citywide change.",
                "new_evidence":[{"source_id":"EPMC-NOVEL","quote":quote,"role":"qualifies"}],
                "scope_risk":"No locality-specific denominators or independent impact evaluation.",
                "alternative_explanation":"Changing visibility across repeated surveys.",
                "next_test":"Use detection-calibrated longitudinal observation of the same population."}]}
        raise AssertionError("Unexpected prompt")

def a_search(q,*,limit):return [dict(NEW_A)]
def o_search(q,*,limit):return [dict(NEW_O)]

class AuditTests(unittest.TestCase):
    def original(self,folder):
        c=InvestigationController(folder,reasoner=StubReasoner(),
             academic_search=lambda q,*,limit:[dict(SOURCES["EPMC-123456789012"])],
             official_search=lambda q,*,limit:[dict(SOURCES["OFFICIAL-987654321012"])])
        state=c.start("Why does monitoring rabies prevention populations fail?",MODULES,max_rounds=1)
        for _ in range(5):state=c.step(state["id"])
        self.assertEqual(state["stage"],"ready_next")
        return c,state

    def test_independent_source_challenge_staged_without_promoting_claim(self):
        with TemporaryDirectory() as root:
            original,state=self.original(root)
            before=deepcopy(original.app.store.load())
            model=Judge()
            audit=ChallengeController(root,reasoner=model,academic_search=a_search,official_search=o_search)
            s=audit.start(state["id"])
            for phase in ["collect","judge","stage","done"]:
                s=audit.step(s["id"]);self.assertEqual(s["stage"],phase)
                self.assertEqual(audit.load(s["id"])["stage"],phase)
            self.assertEqual(s["findings"]["findings"][0]["verdict"],"scope_qualified")
            self.assertEqual(len(s["sources"]),2)
            self.assertEqual(len(s["packet"]["nodes"]),3)
            self.assertEqual(len(s["packet"]["edges"]),2)
            self.assertEqual([e["status"] for e in s["packet"]["edges"]].count("unresolved"),1)
            self.assertTrue(all(n["layer"]=="neutral" for n in s["packet"]["nodes"]))
            after=original.app.store.load()
            self.assertEqual({k:v["status"] for k,v in before["semantic_edges"].items()},
                             {k:after["semantic_edges"][k]["status"] for k in before["semantic_edges"]})
            repeated=original.graph.ingest_packet(state["project_id"],s["packet"])
            self.assertEqual(repeated["id"],s["graph_receipt"]["id"])
            self.assertEqual(after,original.app.store.load())
            self.assertNotIn("Free roaming dog counts can suffer",model.prompts[0])

    def test_credible_but_wrong_topic_cannot_be_used_as_independent_evidence(self):
        original=[{"statement":"Dogs requiring sterilization declined during the dog-population intervention."}]
        unrelated={"title":"Population ageing and health literacy","text":
                   "Public health officials are studying the ageing of human populations."}
        related={"title":"Free-roaming dogs and sterilization coverage","text":
                 "Dog sterilization campaigns require careful denominator definition."}
        self.assertFalse(source_topic_fit(original,unrelated))
        self.assertTrue(source_topic_fit(original,related))

    def test_false_new_source_quote_forces_inconclusive(self):
        trial={"assessments":[{"claim_id":"R1:P1","verdict":"conflicting",
             "rationale":"Invented impact finding from nonexistent quotation.",
             "new_evidence":[{"source_id":"EPMC-NOVEL","quote":"nonexistent 50 percent trial proves outcome","role":"challenges"}]}]}
        result=validate_adjudication([{"claim_id":"R1:P1"}],[NEW_A],trial)
        self.assertEqual(result["findings"][0]["verdict"],"inconclusive")
        self.assertEqual(len(result["rejected"]),1)

    def test_missing_evidence_family_stops_without_graph_mutation(self):
        with TemporaryDirectory() as root:
            original,state=self.original(root)
            prior=original.app.store.load()
            audit=ChallengeController(root,reasoner=Judge(),academic_search=a_search,
                    official_search=lambda q,*,limit:[])
            s=audit.start(state["id"])
            for phase in ["collect","needs_sources","collect","blocked"]:
                s=audit.step(s["id"]);self.assertEqual(s["stage"],phase)
            self.assertIsNone(s["graph_receipt"])
            self.assertEqual(prior,original.app.store.load())

    def test_provider_failure_resumes_same_stage(self):
        with TemporaryDirectory() as root:
            _,state=self.original(root)
            model=Judge(fail=True)
            audit=ChallengeController(root,reasoner=model,academic_search=a_search,official_search=o_search)
            s=audit.start(state["id"])
            with self.assertRaises(TimeoutError):audit.step(s["id"])
            failed=audit.load(s["id"])
            self.assertEqual(failed["stage"],"plan")
            self.assertEqual(failed["last_error"]["error_type"],"TimeoutError")
            self.assertEqual(audit.step(s["id"])["stage"],"collect")

if __name__=="__main__":unittest.main()
