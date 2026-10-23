"""Competitor-relative progress honesty gate: no invented head-to-head scores.

This checks source-backed coverage and release claims, NOT competitor model
performance. Real comparative task outputs are mandatory before upgrade to parity.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research_materials/competitive_reference/competitor_relative_progress_v1.json"
DOC=ROOT/"docs/COMPETITOR_ANCHORED_INTELLIGENCE_SCORECARD_2026_10_23.md"
TEMPLATE=ROOT/".github/pull_request_template.md"


def validate_baselines(data):
    assert data.get("schema")=="cite_refinery.competitor_relative_progress.v1"
    assert data.get("as_of")=="2026-10-23"
    items=data.get("alternatives")
    assert isinstance(items,list) and len(items)>=7
    ids=set()
    per=Counter()
    for row in items:
        assert isinstance(row,dict) and row.get("id") not in ids
        ids.add(row["id"])
        assert row.get("map") in {"practical","academic","implementation","cross_layer"}
        per[row["map"]]+=1
        assert all(isinstance(row.get(k),str) and len(row[k])>=9
                   for k in ("name","url","documented_capability","evidence_kind",
                             "atlas_gap","required_test"))
        for k in ("url","repository"):
            if row.get(k):
                p=urlsplit(row[k])
                assert p.scheme=="https" and p.hostname and not p.username
        assert type(row.get("direct_head_to_head_measured")) is bool
        if row["direct_head_to_head_measured"]:
            assert row.get("head_to_head_scope") and "identity" in row["head_to_head_scope"].lower()
            assert row["id"]=="ecosystems_science"
    assert per["academic"]>=2 and per["practical"]>=1
    assert per["implementation"]>=1 and per["cross_layer"]>=1
    m=data["metrics"]
    assert m["source_cards"]["total"]==sum(m["source_cards"][k]
                              for k in ("practical","academic","implementation"))==1497
    assert m["semantic_navigation"]["development_paraphrase_targets"]==10
    assert m["semantic_navigation"]["minilm_top5"]==8
    assert not m["semantic_navigation"]["independent_gold"]
    assert m["science_catalogue"]["science_matched_identities"]+m["science_catalogue"]["science_unmatched"]==1287
    assert not m["science_catalogue"]["functionality_verified_by_catalogue"]
    assert m["source_claim_triage"]["minilm_supported_candidates_matched_reference"]==0
    assert m["source_claim_triage"]["deberta_supported_candidates_matched_reference"]==2
    assert not m["source_claim_triage"]["source_offsets_and_gold_independently_adjudicated"]
    gate=data["competitive_release_gate"]
    assert gate["status"]=="NOT_RUN"
    assert gate["real_task_level_head_to_head_total"]==0
    assert gate["independently_adjudicated_task_count_minimum"]>=30
    assert gate["no_claimed_competitor_outperformance_without_direct_receipts"]
    assert gate["candidate_comparator_answer_receipts_required"]
    assert gate["source_access_parity_required"]
    assert gate["original_source_quote_offsets_verified"]
    assert gate["software_functional_execution_separate_from_topic_similarity"]
    assert gate["false_candidate_supported_claims_reported"]
    assert gate["unanswerable_abstention_reported"]
    assert gate["latency_and_cost_reported"]
    assert gate["measured_intelligence_advantage_claim"] is False
    return True


class CompetitorAnchoredProgressTests(unittest.TestCase):
    def test_registry_valid_and_no_self_claimed_competitor_win(self):
        d=json.loads(PATH.read_text("utf-8"))
        self.assertTrue(validate_baselines(d))

    def test_living_review_artifacts_require_comparators_and_no_fake_scores(self):
        doc=DOC.read_text("utf-8")
        template=TEMPLATE.read_text("utf-8")
        for name in ("PaperQA2","OpenScholar","OpenAleph","ecosyste.ms Science","ORKG"):
            self.assertIn(name,doc)
        for phrase in ("NOT_EVALUATED","source access","abstention","false",
                       "head-to-head"):
            self.assertIn(phrase.lower(),(doc+"\n"+template).lower())
        self.assertIn("Nearest competitor",template)
        self.assertIn("What we are still worse at",template)

    def test_cannot_silently_promote_comparative_outperformance(self):
        d=json.loads(PATH.read_text("utf-8"))
        d["competitive_release_gate"]["measured_intelligence_advantage_claim"]=True
        with self.assertRaises(AssertionError):
            validate_baselines(d)

    def test_cannot_mistake_catalogue_overlap_for_actual_test(self):
        d=json.loads(PATH.read_text("utf-8"))
        d["metrics"]["science_catalogue"]["functionality_verified_by_catalogue"]=True
        with self.assertRaises(AssertionError):
            validate_baselines(d)

    def test_cannot_lose_practical_comparator(self):
        d=json.loads(PATH.read_text("utf-8"))
        d["alternatives"]=[r for r in d["alternatives"] if r["map"]!="practical"]
        with self.assertRaises(AssertionError):
            validate_baselines(d)

    def test_no_invented_independent_scientific_gold(self):
        d=json.loads(PATH.read_text("utf-8"))
        d["metrics"]["semantic_navigation"]["independent_gold"]=True
        with self.assertRaises(AssertionError):
            validate_baselines(d)


if __name__=="__main__":
    unittest.main()
