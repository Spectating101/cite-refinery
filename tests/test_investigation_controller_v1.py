"""Persistent investigation controller: contract, source and resume tests."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xml.sax.saxutils import escape

from cite_refinery.investigation_sources import (
    _host_allowed, collect_sources, search_europe_pmc, search_official,
)
from cite_refinery.investigation_controller import (
    InvestigationController,validate_plan,
)


MODULES=[
    {"id":"AW-01","title":"Free roaming dog population estimation",
     "summary":"Detection probability and population coverage"},
    {"id":"AW-03","title":"Dog vaccination and rabies health services",
     "summary":"Population vaccination and access to PEP"},
]
SOURCES={
    "EPMC-123456789012":{
        "id":"EPMC-123456789012","url":"https://doi.org/10.1/dog",
        "text":"Free roaming dog counts can suffer heterogeneous detection probability and may require repeated mark recapture surveys.",
        "origin_type":"scholarly_abstract_lead",
        "source_scope":"A candidate academic abstract, not a validated full article.",
    },
    "OFFICIAL-987654321012":{
        "id":"OFFICIAL-987654321012","url":"https://www.who.int/rabies",
        "text":"Dog vaccination and timely human post exposure prophylaxis are complementary means of preventing human rabies.",
        "origin_type":"official_webpage_excerpt_unverified",
        "source_scope":"Institutional summary, not local realized impact.",
    },
}
PLAN={"focus":"Whether detection-biased counts and PEP access affect dog-rabies programme evaluation",
      "reason":"Compare study design limitations and normative policy recommendations against service access.",
      "hypotheses":["Reported free roaming counts may omit less visible dogs."],
      "queries":[{"lane":"academic","query":"free roaming dog abundance heterogeneous detection rabies"},
                 {"lane":"official","query":"rabies dog vaccination PEP One Health WHO"}]}


class StubReasoner:
    def __init__(self,fail_once=False):
        self.calls=[]
        self.fail_once=fail_once
    def __call__(self,prompt):
        self.calls.append(prompt)
        if self.fail_once:
            self.fail_once=False
            raise TimeoutError("inference backend unavailable")
        if "INVESTIGATION PLANNER" in prompt or "SOURCE-RECOVERY PLANNER" in prompt:
            return copy.deepcopy(PLAN)
        if "RESEARCH REASONER" in prompt:
            return {"propositions":[
                {"id":"P1","statement":"Observed dog counts may be affected by heterogeneous detection probability.",
                 "claim_type":"reported_limitation","module_ids":["AW-01"],
                 "support":[{"source_id":"EPMC-123456789012",
                             "quote":"Free roaming dog counts can suffer heterogeneous detection probability"}],
                 "scope":"This academic abstract is not a population survey for a specific region.",
                 "limitation":"Does not establish any actual intervention effect."},
                {"id":"P2","statement":"Dog vaccination and timely PEP are complementary rabies-prevention measures.",
                 "claim_type":"program_capability","module_ids":["AW-03"],
                 "support":[{"source_id":"OFFICIAL-987654321012",
                             "quote":"Dog vaccination and timely human post exposure prophylaxis are complementary"}],
                 "scope":"Public health guidance, not a locality's observed care access.",
                 "limitation":"Does not establish vaccine coverage or clinic capacity."}],
                "bridges":[
                    {"from":"P1","to":"P2","relation":"QUALIFIES",
                     "reason":"Counts may be an unreliable program denominator; preventive treatment remains a separate component.",
                     "limitations":"No linked local denominator or PEP outcomes have been observed."}],
                "open_questions":[{
                    "question":"Which underserved districts lack reliable dog vaccination denominators and timely PEP access?",
                    "module_ids":["AW-01","AW-03"],
                    "why_unresolved":"Current abstracts and guidelines do not establish site-specific coverage."}]}
        if "skeptical source-entailment REVIEWER" in prompt:
            return {"reviews":[
                {"proposition_id":"P1","verdict":"entailed",
                 "quote":"Free roaming dog counts can suffer heterogeneous detection probability",
                 "rationale":"The source says observed dog counts may have detection problems.",
                 "scope_risks":"No site-specific population effect."},
                {"proposition_id":"P2","verdict":"entailed",
                 "quote":"Dog vaccination and timely human post exposure prophylaxis are complementary",
                 "rationale":"The institutional guidance directly states the complementary program roles.",
                 "scope_risks":"Local uptake is unknown."}],
                "bridge_reviews":[
                    {"from":"P1","to":"P2","verdict":"uncertain",
                     "rationale":"The individual propositions do not establish direct measured cross-field dependence."}]}
        raise AssertionError("Unexpected prompt")


def academic_stub(query,*,limit):
    return [dict(SOURCES["EPMC-123456789012"])]
def official_stub(query,*,limit):
    return [dict(SOURCES["OFFICIAL-987654321012"])]


class ControllerTests(unittest.TestCase):
    def make(self,dir,reasoner=None):
        return InvestigationController(dir,reasoner=reasoner or StubReasoner(),
                                       academic_search=academic_stub,
                                       official_search=official_stub)

    def test_plan_is_an_actual_llm_decision_with_independent_queries(self):
        validated=validate_plan(copy.deepcopy(PLAN))
        self.assertEqual({q["lane"] for q in validated["queries"]},{"academic","official"})
        with self.assertRaises(ValueError):
            validate_plan(dict(PLAN,queries=[{"lane":"academic","query":"dogs"}]))

    def test_complete_round_persists_sources_critique_and_graph(self):
        with TemporaryDirectory() as folder:
            llm=StubReasoner()
            c=self.make(folder,llm)
            s=c.start("Why do animal rabies prevention programs fail?",MODULES,max_rounds=2)
            session_id=s["id"]
            self.assertFalse(s["rounds"])
            # Four durable work stages and one durable graph-stage check.
            for stage in ("collect","reason","critique","stage","ready_next"):
                s=c.step(session_id)
                self.assertEqual(s["stage"],stage)
                self.assertEqual(c.load(session_id)["stage"],stage)
            self.assertEqual(len(s["rounds"][0]["sources"]),2)
            self.assertEqual(s["rounds"][0]["source_count"],2)
            self.assertEqual(len(s["rounds"][0]["inspected"]["propositions"]),2)
            self.assertEqual(len(s["rounds"][0]["inspected"]["bridges"]),1)
            self.assertEqual(len(s["rounds"][0]["open_questions"]),1)
            self.assertEqual(len(s["frontier"]),1)
            r=s["rounds"][0]
            self.assertEqual(r["packet"]["conversion_metadata"]["verified_effectiveness_claims"],0)
            self.assertTrue(all(n["layer"]=="neutral" for n in r["packet"]["nodes"]))
            self.assertIn("unresolved",{e["status"] for e in r["packet"]["edges"]})
            self.assertEqual(s["authority"],"candidate_neutral_only")
            before=c.app.store.load()
            self.assertGreater(len(before["semantic_nodes"]),0)
            self.assertEqual(c.graph.ingest_packet(s["project_id"],r["packet"])["id"],
                             r["graph_receipt"]["id"])
            self.assertEqual(before,c.app.store.load())
            # Another controller instance resumes from the saved checkpoint.
            resumed=self.make(folder,StubReasoner())
            s2=resumed.step(session_id)
            self.assertEqual(s2["stage"],"plan")
            self.assertIn("underserved",s2["focus"])
            self.assertEqual(len(s2["visited_questions"]),1)
            # Modules are preselected ontology; no source bibliography was given to start.
            self.assertTrue(all("source" not in x for x in MODULES))

    def test_large_generated_answer_has_bounded_review_and_explicit_pending(self):
        with TemporaryDirectory() as folder:
            controller=self.make(folder,StubReasoner())
            s=controller.start("Why do dog vaccination programmes lack validated outcomes?",MODULES)
            for _ in range(3):s=controller.step(s["id"])
            self.assertEqual(s["stage"],"critique")
            base=s["rounds"][0]["inspected"]
            prototype=copy.deepcopy(base["propositions"][0])
            for number in range(3,27):
                row=copy.deepcopy(prototype)
                row["id"]=f"P{number}"
                row["statement"]+=f" Research comparison {number}."
                base["propositions"].append(row)
            controller.save(s)
            reviewed=controller.step(s["id"])
            self.assertEqual(reviewed["stage"],"stage")
            ratio=reviewed["rounds"][0]["review_coverage"]
            self.assertEqual(ratio["total_propositions"],26)
            self.assertEqual(ratio["propositions_in_model_review"],18)
            verdicts=reviewed["rounds"][0]["critique"]["propositions"]
            self.assertEqual(len(verdicts),26)
            self.assertGreaterEqual(sum(v["reviewer_verdict"]=="uncertain" for v in verdicts),8)
            self.assertTrue(ratio["unreviewed_are_explicitly_uncertain"])

    def test_failure_retains_stage_and_retry_does_not_duplicate_round(self):
        with TemporaryDirectory() as folder:
            reasoner=StubReasoner(fail_once=True)
            c=self.make(folder,reasoner)
            s=c.start("Why do rabies programmes fail with weak survey evidence?",MODULES)
            with self.assertRaises(TimeoutError):
                c.step(s["id"])
            failed=c.load(s["id"])
            self.assertEqual(failed["stage"],"plan")
            self.assertEqual(failed["last_error"]["kind"],"TimeoutError")
            self.assertEqual(len(failed["rounds"]),0)
            retry=c.step(s["id"])
            self.assertEqual(retry["stage"],"collect")
            self.assertEqual(len(retry["rounds"]),1)
            self.assertIsNone(retry["last_error"])

    def test_incomplete_acquisition_replans_instead_of_hallucinating(self):
        counter={"official":0}
        def official_on_retry(query,*,limit):
            counter["official"]+=1
            if counter["official"]==1:
                return []
            return official_stub(query,limit=limit)
        with TemporaryDirectory() as folder:
            reasoner=StubReasoner()
            controller=InvestigationController(folder,reasoner=reasoner,
                            academic_search=academic_stub,
                            official_search=official_on_retry)
            session=controller.start("Why do canine rabies programmes have weak evidence?",MODULES)
            controller.step(session["id"])
            first=controller.step(session["id"])
            self.assertEqual(first["stage"],"needs_sources")
            self.assertEqual(first["rounds"][0]["source_count"],1)
            self.assertEqual(first["rounds"][0]["source_attempts"],1)
            revised=controller.step(session["id"])
            self.assertEqual(revised["stage"],"collect")
            self.assertEqual(len(revised["rounds"][0]["recovery_plans"]),1)
            refreshed=controller.step(session["id"])
            self.assertEqual(refreshed["stage"],"reason")
            self.assertEqual(refreshed["rounds"][0]["source_count"],2)
            self.assertEqual(refreshed["rounds"][0]["source_attempts"],2)
            self.assertEqual(len(refreshed["rounds"][0]["sources"]),2)
            self.assertEqual(len(refreshed["rounds"][0].get("inspected",{})),0)

    def test_missing_critical_family_blocks_after_three_attempts(self):
        with TemporaryDirectory() as folder:
            ctrl=InvestigationController(folder,reasoner=StubReasoner(),
                   academic_search=academic_stub,
                   official_search=lambda query,*,limit: [])
            s=ctrl.start("Why do dog vaccination programmes have missing monitoring evidence?",MODULES)
            for _ in range(6):
                s=ctrl.step(s["id"])
            self.assertEqual(s["stage"],"blocked")
            self.assertEqual(s["rounds"][0]["source_attempts"],3)
            self.assertFalse(s["rounds"][0].get("inspected"))

    def test_source_discovery_search_lane_dedup(self):
        out=collect_sources(PLAN["queries"],academic_search=academic_stub,official_search=official_stub)
        self.assertEqual(out["sources_acquired"],2)
        self.assertEqual(out["failures"],[])
        self.assertEqual({x["origin_type"] for x in out["sources"]},
                         {"scholarly_abstract_lead","official_webpage_excerpt_unverified"})

    def test_public_source_domain_guard_and_response_length(self):
        for dangerous in [
            "http://who.int/article","https://who.int.bad.example/article",
            "https://127.0.0.1/","https://user:pass@who.int/test",
            "https://who.int:8080/article",
        ]:
            self.assertFalse(_host_allowed(dangerous),dangerous)
        self.assertTrue(_host_allowed("https://www.who.int/rabies"))

    def test_real_provider_parsers_with_injected_http_results(self):
        epmc={"resultList":{"result":[{
            "title":"Free roaming dog methods",
            "doi":"10.1/12345",
            "abstractText":"Observational population sampling frequently omits animals that are difficult to observe, creating inconsistent survey results and statistical estimation challenges.",
        }]}}
        def epmc_http(url,**kwargs):
            return json.dumps(epmc).encode(),url,"application/json"
        r=search_europe_pmc("free roaming dogs",fetch=epmc_http)
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["origin_type"],"scholarly_abstract_lead")
        fake_listing="""<html><body><a href="https://www.who.int/example">Rabies prevention WHO</a>
        <a href="https://who.int.evil.test/phish">Imposter</a></body></html>"""
        fake_html="""<html><body><p>Rabies prevention programs depend on dog vaccination,
        continued case surveillance, community outreach and timely access to
        human post-exposure prophylaxis services.</p></body></html>"""
        def rss_http(url,**kwargs):
            if "search.brave.com" in url:return fake_listing.encode(),url,"text/html"
            return fake_html.encode(),url,"text/html"
        hits=search_official("rabies vaccination",fetch=rss_http)
        self.assertEqual(len(hits),1)
        self.assertEqual(hits[0]["url"],"https://www.who.int/example")
        self.assertIn("prophylaxis",hits[0]["text"])


if __name__=="__main__":
    unittest.main()
