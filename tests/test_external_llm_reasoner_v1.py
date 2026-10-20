"""An LLM must do semantic interpretation; Cite-Refinery must bound it."""
from __future__ import annotations
import copy
import json
import unittest
from tempfile import TemporaryDirectory

from cite_refinery import CiteRefinery,SemanticGraph
from cite_refinery.external_llm_reasoner import (make_input,build_prompt,inspect_answer,
    build_second_pass_prompt,inspect_second_pass)
from cite_refinery.external_llm_packets import llm_review_packet
from cite_refinery.external_llm_runtime import _parse_response,LLMUnavailable


class ReasoningContractTests(unittest.TestCase):
    def setUp(self):
        self.raw_sources=[{
            "id":"WMO","url":"https://example.org/wmo",
            "text":"HydroSOS is the backbone supporting the Early Warnings for All initiative for hydrological disasters. Monitoring hydrological status does not alone document the measured effect of an intervention.",
            "origin_type":"official_institution","source_scope":"Institutional framework",
        }]
        self.modules=[
            {"id":"WA-06","title":"Hydrological monitoring",
             "summary":"Assess status and forecasting"},
            {"id":"DR-01","title":"Early-warning dissemination",
             "summary":"Warning coverage and effective delivery"},
        ]
        self.data=make_input(self.raw_sources,self.modules)
        self.reply={
            "propositions":[
                {"id":"P1","statement":"HydroSOS is described as supporting an early-warning initiative for hydrological disasters.",
                 "claim_type":"program_capability","module_ids":["WA-06"],
                 "support":[{"source_id":"WMO","quote":"HydroSOS is the backbone supporting the Early Warnings for All initiative for hydrological disasters"}],
                 "scope":"WMO initiative, hydrological disasters","limitation":"No observed mortality reduction is established"},
                {"id":"P2","statement":"Early Warnings for All receives described support from HydroSOS in hydrological disaster contexts.",
                 "claim_type":"definition","module_ids":["DR-01"],
                 "support":[{"source_id":"WMO","quote":"the Early Warnings for All initiative for hydrological disasters"}],
                 "scope":"Initiative naming; not local delivery","limitation":"Actual alert reach and response remain unmeasured"},
                {"id":"P3","statement":"HydroSOS caused an annual mortality reduction of 20 percent.",
                 "claim_type":"research_finding","module_ids":["WA-06"],
                 "support":[{"source_id":"WMO","quote":"HydroSOS caused deaths to fall by 20%"}],
                 "scope":"Global claim","limitation":"None"},
            ],
            "bridges":[
                {"from":"P1","to":"P2","relation":"CONTEXT_FOR",
                 "reason":"The quoted sentence explicitly links the two institutional initiatives.",
                 "limitations":"No separately validated field outcome, causality or local deployment"},
                {"from":"P1","to":"P2","relation":"CAUSES",
                 "reason":"Causal outcome allegedly exists.","limitations":"No test"},
                {"from":"P1","to":"P3","relation":"RELATED_TO",
                 "reason":"Undocumented mortality outcome claim.","limitations":"No source"},
            ],
            "open_questions":[
                {"question":"Did hydrological warning delivery improve measured response in an identifiable community?",
                 "module_ids":["WA-06","DR-01"],"why_unresolved":"Source speaks to institutional support, not local outcomes"}
            ],
        }

    def test_prompt_is_llm_centered_and_source_preserving(self):
        prompt=build_prompt(self.data)
        self.assertIn("RESEARCH REASONER",prompt)
        self.assertIn("ATOMIC",prompt)
        self.assertIn(self.raw_sources[0]["text"],prompt)
        self.assertIn("WA-06",prompt)
        self.assertIn("DR-01",prompt)
        self.assertNotIn("P3",prompt)
        self.assertEqual(len(self.data["sources"][0]["text_sha256"]),64)

    def test_quote_gate_filters_fabricated_outcome_and_causal_edge(self):
        report=inspect_answer(self.data,self.reply)
        self.assertEqual([p["id"] for p in report["propositions"]],["P1","P2"])
        self.assertEqual(len(report["bridges"]),1)
        self.assertEqual(report["bridges"][0]["status"],"candidate")
        self.assertEqual(len(report["open_questions"]),1)
        self.assertEqual(len(report["rejected"]),3)
        self.assertEqual({x["reason"] for x in report["rejected"]},
                         {"source_quote_missing_or_invented","unverified_relation_or_missing_endpoint"})
        self.assertIn("NOT been established",report["qualification"])

    def test_schema_rejects_unrecognized_modules_and_missing_source(self):
        bad=copy.deepcopy(self.reply)
        bad["propositions"][0]["module_ids"]=["UN-99"]
        bad["propositions"][1]["support"][0]["source_id"]="INVENTED"
        report=inspect_answer(self.data,bad)
        self.assertFalse(report["propositions"])
        self.assertFalse(report["bridges"])
        with self.assertRaises(ValueError):
            make_input([dict(self.raw_sources[0],url="http://wrong.example")],self.modules)

    def test_candidate_packet_keeps_all_propositions_neutral(self):
        report=inspect_answer(self.data,self.reply)
        packet=llm_review_packet(self.data,report)
        self.assertEqual(packet["schema"],"cite_refinery.semantic_graph.v1")
        self.assertEqual(packet["conversion_metadata"]["propositions"],2)
        self.assertEqual(packet["conversion_metadata"]["verified_effectiveness_claims"],0)
        self.assertEqual(len(packet["nodes"]),6)
        self.assertEqual(len(packet["edges"]),5)
        self.assertTrue(all(n["layer"]=="neutral" for n in packet["nodes"]))
        self.assertTrue(all(e["status"]=="candidate" for e in packet["edges"]))
        self.assertTrue(all(e["relation"]=="CONTEXT_FOR" for e in packet["edges"]))
        with TemporaryDirectory() as directory:
            app=CiteRefinery(directory)
            project=app.init_project("Semantic reasoning review","No accepted authority")
            graph=SemanticGraph(app.store)
            a=graph.ingest_packet(project.id,packet)
            snapshot=app.store.load()
            b=graph.ingest_packet(project.id,packet)
            self.assertEqual(a["id"],b["id"])
            self.assertEqual(app.store.load(),snapshot)

    def test_second_llm_can_criticize_even_quote_matching_statements(self):
        first=inspect_answer(self.data,self.reply)
        critic_prompt=build_second_pass_prompt(self.data,first)
        self.assertIn("skeptical source-entailment REVIEWER",critic_prompt)
        self.assertIn("HydroSOS",critic_prompt)
        critique={"reviews":[
            {"proposition_id":"P1","verdict":"entailed",
             "quote":"HydroSOS is the backbone supporting the Early Warnings for All initiative for hydrological disasters",
             "rationale":"The institutional link is stated explicitly.",
             "scope_risks":"No mortality effect"},
            {"proposition_id":"P2","verdict":"entailed",
             "quote":"This made-up source sentence is not in the WMO passage",
             "rationale":"Incorrectly assumes support.","scope_risks":"Unvalidated"}],
            "bridge_reviews":[
                {"from":"P1","to":"P2","verdict":"plausible",
                 "rationale":"The quoted institutional support may connect both questions."}]}
        second=inspect_second_pass(self.data,first,critique)
        verdicts={x["proposition_id"]:x["reviewer_verdict"] for x in second["propositions"]}
        self.assertEqual(verdicts,{"P1":"entailed","P2":"uncertain"})
        self.assertEqual(second["bridges"][0]["reviewer_verdict"],"uncertain")
        self.assertEqual(second["state"],"CRITICAL_SECOND_PASS_NOT_AUTHORITY")
        self.assertTrue(all(x["authority"]=="NONE_ACCEPTED" for x in second["propositions"]))

    def test_explicit_model_response_wrapper(self):
        ans={"propositions":[],"bridges":[],"open_questions":[]}
        self.assertEqual(_parse_response({"result":json.dumps(ans)}),ans)
        self.assertEqual(_parse_response({"structured_output":ans}),ans)
        with self.assertRaises(LLMUnavailable):
            _parse_response("not json")


if __name__=="__main__":
    unittest.main()
