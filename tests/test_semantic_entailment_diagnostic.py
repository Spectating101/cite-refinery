"""Check integrity and epistemic boundaries of blind-to-reference abstract reading."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from cite_refinery.semantic_entailment_diagnostic import (
    prepare,judge_prompt,adjudicate,evaluate,bounded_excerpt,
)

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"

def casebook():
    return json.loads((ROOT/"semantic_entailment_casebook.json").read_text(encoding="utf-8"))

def fixture():
    c=casebook()
    text=("A measured observational survey found a positive association between "
          "variables in one study population. The evidence did not test whether an "
          "intervention improved clinical outcomes. Randomization did not take place.")
    lookup={}
    for case in c["cases"]:
        lookup[case["source_id"]]=text
    sources=[]
    for sid,t in lookup.items():
        sources.append({
            "id":sid,"url":"https://example.org/"+sid,"title":"Mock "+sid,
            "text":t,"sha256":hashlib.sha256(t.encode()).hexdigest(),
            "source_scope":"Synthetic observational abstract, no intervention testing",
        })
    corpus={"schema":"cite_refinery.open_corpus.v1",
            "material_type":"unclassified_source_records","sources":sources}
    return c,corpus

def raw(packet):
    return {"judgments":[{
        "id":x["id"],"label":"overreach",
        "quote":"The evidence did not test whether an intervention improved clinical outcomes.",
        "reason":"The claim goes beyond the measured association in the provided observational study.",
        "scope_caveat":"The synthetic source is observational and reports no tested intervention in this population.",
    } for x in packet["cases"]]}

class SourceEntailmentDiagnosticTests(unittest.TestCase):
    def test_blind_packet_hides_reference_and_gold_reason(self):
        cases,corpus=fixture()
        packets=prepare(cases,corpus)
        self.assertEqual(len(packets),8)
        self.assertTrue(all(len(p["cases"])==3 for p in packets))
        for p in packets:
            prompt=judge_prompt(p)
            self.assertNotIn('"expected"',prompt)
            self.assertNotIn('"gold_reason"',prompt)
            self.assertIn("population",prompt)
            self.assertIn("outcome",prompt)

    def test_exact_quote_and_complete_set_required(self):
        cases,corpus=fixture()
        packet=prepare(cases,corpus)[0]
        good=adjudicate(packet,raw(packet))
        self.assertEqual(len(good["judgments"]),3)
        self.assertTrue(all(not x["native_status_change_authorized"]
                            for x in good["judgments"]))
        self.assertRaises(ValueError,bounded_excerpt,
            packet["cases"][0]["abstract_text"],"This is a completely fabricated quote from nowhere.")
        bad=raw(packet);bad["judgments"][0]["quote"]="Nonexistent fabricated passage about policy decisions and some concepts."
        with self.assertRaisesRegex(ValueError,"not found"):
            adjudicate(packet,bad)
        bad=raw(packet);bad["judgments"]=bad["judgments"][:-1]
        with self.assertRaisesRegex(ValueError,"incomplete"):
            adjudicate(packet,bad)
        bad=raw(packet);bad["judgments"][1]["id"]=bad["judgments"][0]["id"]
        with self.assertRaisesRegex(ValueError,"duplicate"):
            adjudicate(packet,bad)

    def test_source_hash_and_exact_membership(self):
        cases,corpus=fixture()
        bad=deepcopy(corpus)
        bad["sources"][0]["text"]+=" changed after retrieval"
        with self.assertRaisesRegex(ValueError,"SHA"):
            prepare(cases,bad)
        bad=deepcopy(cases)
        bad["cases"][0]["source_id"]="INVENTED_ID"
        with self.assertRaisesRegex(ValueError,"matching original"):
            prepare(bad,corpus)

    def test_evaluation_keeps_disagreement_and_no_promotion(self):
        cases,corpus=fixture()
        packets=prepare(cases,corpus)
        audits=[adjudicate(p,raw(p)) for p in packets]
        out=evaluate(cases,packets,audits)
        self.assertEqual(out["n_cases"],24)
        self.assertEqual(out["reference_classes"],{
            "entailed":8,"contradicted":8,"overreach":8})
        self.assertFalse(out["graph_promotion_allowed"])
        self.assertEqual(out["false_entailment_count"],0)
        self.assertTrue(any(not x["agreement"] for x in out["cases"]))
        audits[0]["judgments"][0]["native_status_change_authorized"]=True
        with self.assertRaisesRegex(ValueError,"promoted"):
            evaluate(cases,packets,audits)

    def test_real_diagnostic_output_never_promotes(self):
        path=ROOT/"semantic_entailment_diagnostic_results.json"
        if not path.exists():
            self.skipTest("model diagnostic results not collected in this environment")
        out=json.loads(path.read_text())
        self.assertEqual(out["n_cases"],24)
        self.assertFalse(out["graph_promotion_allowed"])
        self.assertEqual(len(out["cases"]),24)
        self.assertEqual(len({x["id"] for x in out["cases"]}),24)
        self.assertTrue(all(not x["human_adjudication_complete"]
                            and not x["commercial_or_scientific_status_promoted"]
                            for x in out["cases"]))
        self.assertTrue(all(len(x["quote"].split())<=24 for x in out["cases"]))

if __name__=="__main__":
    unittest.main()
