"""Testing source-verified but non-authoritative cross-study mechanism challenges."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from cite_refinery.cross_source_mechanism_critic import inputs,prompt,validate,summarize,markdown

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"

def fixture():
    source_text="A cross-sectional observational study of participants in two countries reports exposures and location-specific outcomes. There was no trial to evaluate a deployed intervention or estimate its causal benefits."
    corpus={"schema":"cite_refinery.open_corpus.v1",
            "sources":[]}
    citations=[]
    for i in range(2):
        key="ID-"+str(i)
        url="https://example.org/"+key
        sha=hashlib.sha256(source_text.encode()).hexdigest()
        corpus["sources"].append({"id":key,"url":url,"text":source_text,
                                   "title":key,"source_scope":"abstract only",
                                   "sha256":sha})
        citations.append({"id":key,"url":url,"original_sha256":sha,
                          "quote":"There was no trial to evaluate a deployed intervention"})
    primary={"schema":"cite_refinery.primary_mechanism_graph.v1",
             "briefs":[{
                 "id":"mechanism:synthetic_field_problem",
                 "problem":"Actual impact of an intervention in specific field conditions is not known.",
                 "mechanism":"Exposure and observational correlations may depend on site and population.",
                 "capability_contract":"Require independent intervention evaluation and technical verification.",
                 "primary_sources":citations,"implementation_lead":None,
             }]}
    return primary,corpus

def response(case):
    return {
        "id":case["id"],"assessment":"partial_support","source_id":case["sources"][0]["id"],
        "quote":"There was no trial to evaluate a deployed intervention or estimate its causal benefits.",
        "what_is_supported":"An observational association was reported in a location-specific population.",
        "unsupported_leap":"There is no trial substantiating intervention health effects or technical compatibility.",
        "next_decisive_check":"Inspect the study methods and reproduce a controlled intervention assessment.",
        "implementation_scope":"No specific software component or validated intervention candidate is provided.",
        "cross_source_warning":"The two study populations are not necessarily comparable to other regions.",
    }

class MechanismAdversarialTest(unittest.TestCase):
    def test_bounded_source_and_source_id_against_original(self):
        primary,corpus=fixture()
        cases=inputs(primary,corpus)
        self.assertEqual(len(cases),1)
        self.assertIn("causal",prompt(cases[0]))
        reviewed=validate(cases[0],response(cases[0]))
        self.assertEqual(reviewed["assessment"],"partial_support")
        self.assertFalse(reviewed["accepted_academic_edge"])
        self.assertFalse(reviewed["validated_implementation"])
        bad=deepcopy(response(cases[0]));bad["source_id"]="unlisted"
        with self.assertRaisesRegex(ValueError,"invented source"):
            validate(cases[0],bad)
        bad=deepcopy(response(cases[0]));bad["quote"]="An invented source paragraph about future climate and human health exposure."
        with self.assertRaisesRegex(ValueError,"not found"):
            validate(cases[0],bad)

    def test_source_change_or_unauthorized_promotion_fails(self):
        p,c=fixture()
        c["sources"][0]["text"]+=" changed"
        with self.assertRaisesRegex(ValueError,"tampered source"):
            inputs(p,c)
        p,c=fixture()
        cases=inputs(p,c)
        valid=validate(cases[0],response(cases[0]))
        valid["accepted_academic_edge"]=True
        with self.assertRaisesRegex(ValueError,"forbidden"):
            summarize([valid])

    def test_report_cannot_accept_incomplete_or_duplicate_reviews(self):
        p,c=fixture()
        case=inputs(p,c)[0]
        one=validate(case,response(case))
        with self.assertRaisesRegex(ValueError,"bounded unique"):
            summarize([one,one])
        report=summarize([one])
        self.assertFalse(report["promotion_allowed"])
        self.assertIn("not human-approved",markdown(report))

    def test_real_aggregate_review_is_model_only(self):
        path=ROOT/"cross_source_mechanism_review.json"
        if not path.exists():self.skipTest("model review has not run on this host")
        report=json.loads(path.read_text())
        self.assertEqual(len(report["assessments"]),8)
        self.assertFalse(report["promotion_allowed"])
        self.assertTrue(all(not x["accepted_academic_edge"]
                            and not x["validated_implementation"]
                            and not x["commercial_conversion_confirmed"]
                            for x in report["assessments"]))
        self.assertEqual(len({x["id"] for x in report["assessments"]}),8)

if __name__=="__main__":
    unittest.main()
