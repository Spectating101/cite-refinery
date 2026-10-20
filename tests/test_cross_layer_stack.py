"""Cross-layer behavior tests: demonstrate useful relations and falsification."""
from __future__ import annotations
import copy
import json
import hashlib
from pathlib import Path
import unittest

from cite_refinery.cross_layer_stack import stack_packet
from cite_refinery.cross_layer_proposals import selected_readings, attach_original_excerpts, alignment_prompt, inspect_alignments

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples"


def reviewed_case():
    # The acceptance runner applies reviewer-controlled edge downgrades,
    # source limitations, and missing-link receipts to the frozen original.
    import importlib.util
    spec = importlib.util.spec_from_file_location("dog_acceptance", ROOT / "scripts/acceptance_free_roaming_dogs.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.case_packet(EXAMPLE / "free_roaming_dog_semantic_pilot.json",
                         EXAMPLE / "acceptance_free_roaming_dog_source_review_v1.json")


class StackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = reviewed_case()

    def test_sources_interpretation_and_actionable_missing_link(self):
        out = stack_packet(self.packet)
        observability = next(x for x in out["problems"] if x["problem"]["id"] == "continuous_state_problem")
        self.assertEqual(observability["coverage"], {"practical": True, "academic": True, "program": True})
        kinds = {f["type"] for f in observability["findings"]}
        self.assertIn("method_implementation_mismatch", kinds)
        self.assertIn("scope_qualification", kinds)
        mismatch = next(f for f in observability["findings"] if f["type"] == "method_implementation_mismatch")
        self.assertIn("photograph", mismatch["interpretation"])
        self.assertIn("individual reconciliation", mismatch["interpretation"])
        self.assertIn("requirement", mismatch["why"].lower())
        self.assertEqual([e["relation"] for e in mismatch["reasoning_chain"]],
            ["PARTIALLY_ADDRESSES", "MEASURED_BY", "REQUIRES", "LIMITED_BY", "MISSING_LINK"])
        self.assertTrue(any("icam-coalition" in x for x in mismatch["source_refs"]))
        self.assertEqual(mismatch["review_state"], "unresolved_capability_fit_not_a_proven_incompatibility")
        qualification = next(f for f in observability["findings"] if f["type"] == "scope_qualification")
        self.assertIn("not statistically significant", qualification["interpretation"])
        self.assertEqual(out["authority"], "source_bounded_candidate_interpretation_only")

    def test_deleting_a_crucial_link_removes_the_mismatch(self):
        p = copy.deepcopy(self.packet)
        p["edges"] = [e for e in p["edges"] if not (
            e["relation"] == "MISSING_LINK" and e["source"] == "talea_sighting_photo_limit"
            and e["target"] == "identity_reconciliation_requirement")]
        out = stack_packet(p)
        self.assertFalse(any(f["type"] == "method_implementation_mismatch"
                    for n in out["problems"] for f in n["findings"]))

    def test_same_cluster_is_not_evidence_of_fit(self):
        p = copy.deepcopy(self.packet)
        # unrelated technology with matching cluster and plausible text is NOT linked
        p["nodes"].append({
            "key":"unrelated","statement":"Identity reconciliation AI exists as a product description.",
            "layer":"program","kind":"capability","clusters":["observability"],
            "source_refs":["https://example.org/pitch"]})
        out = stack_packet(p)
        self.assertFalse(any("unrelated" in f["nodes"] for n in out["problems"] for f in n["findings"]))

    def test_legacy_asserted_links_are_not_silent_authority(self):
        raw = json.loads((EXAMPLE / "free_roaming_dog_semantic_pilot.json").read_text())
        out = stack_packet(raw)
        self.assertFalse(any(f["type"] == "method_implementation_mismatch"
                    for p in out["problems"] for f in p["findings"]))

    def test_invalid_graph_is_rejected(self):
        p = copy.deepcopy(self.packet)
        p["edges"][0]["target"] = "unknown"
        with self.assertRaisesRegex(ValueError,"unknown"):
            stack_packet(p)

    def test_integrated_persistent_graph_and_project_isolation(self):
        import tempfile
        from cite_refinery.app import CiteRefinery
        from cite_refinery.semantic import SemanticGraph
        with tempfile.TemporaryDirectory() as tmp:
            app=CiteRefinery(Path(tmp))
            project=app.init_project("Roaming dogs", "Population estimate mismatch").id
            other=app.init_project("Other", "Unrelated project").id
            graph=SemanticGraph(app.store)
            graph.ingest_packet(project, self.packet)
            report=graph.cross_layer_dossier(project)
            self.assertEqual(report["project_id"], project)
            self.assertTrue(any(f["type"]=="method_implementation_mismatch"
                            for p in report["problems"] for f in p["findings"]))
            self.assertEqual(graph.cross_layer_dossier(other)["problems"], [])
            with self.assertRaises(KeyError):
                graph.cross_layer_dossier("nonexistent")

    def test_reproducible_readonly(self):
        p = copy.deepcopy(self.packet)
        one = stack_packet(p)
        self.assertEqual(one, stack_packet(p))
        self.assertEqual(p, self.packet)
        self.assertTrue(one["no_graph_mutation"])


class AutonomousCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = json.loads((ROOT / "research_materials/runtime_trials/open_corpus_20261020/provisional_map.json").read_text())
        a = json.loads((ROOT / "research_materials/runtime_trials/open_corpus_20261020/global_atlas.json").read_text())
        cls.selected = selected_readings(p, a, domain=a["domains"][7]["label"])

    def _answer(self):
        by_layer={}
        for r in self.selected["records"]:
            by_layer.setdefault(r["layer"],[]).append(r["id"])
        return {"alignments":[{
            "practical_ids":by_layer["practical"][:1],
            "academic_ids":by_layer["academic"][:1],
            "program_ids":by_layer["program"][:1],
            "mechanism":"Short-lived perishable surplus requires timely distribution logistics.",
            "interpretation":"The practical constraint could limit implementation reliability, depending on documented collection schedules.",
            "solution_fit":"The program description documents activity without establishing independent nutritional benefits.",
            "evidence_tension":"Different sources measure throughput rather than long-term food security.",
            "counterargument":"Redistribution may supply short-term relief even if systemic food insecurity persists.",
            "next_test":"Compare audited collection and beneficiary nutrition measurements with matched baselines."
        }],"missing_layers":[],"boundary":"All readings remain model-generated hypotheses from this source subset."}

    def test_source_bounded_cross_layer_proposal_and_prompt(self):
        raw = self._answer()
        report = inspect_alignments(self.selected, raw)
        self.assertEqual(report["alignments"][0]["complete_three_layer_stack"], True)
        self.assertEqual(report["alignments"][0]["status"], "llm_candidate_requires_independent_source_review")
        self.assertFalse(report["alignments"][0]["outcome_verified"])
        self.assertIn("Do not match sources solely by shared vocabulary", alignment_prompt(self.selected))

    def test_wrong_perspective_rejected(self):
        bad = self._answer()
        bad["alignments"][0]["program_ids"] = bad["alignments"][0]["academic_ids"]
        result = inspect_alignments(self.selected, bad)
        self.assertEqual(len(result["alignments"]), 0)
        self.assertEqual(result["rejected_candidates"][0]["reason"], "source assigned to wrong perspective")

    def test_absolute_absence_and_causal_proof_rejected(self):
        for invalid in ["No verified intervention exists anywhere.", "The program proves that mortality fell."]:
            answer = self._answer()
            answer["alignments"][0]["interpretation"] = invalid
            result = inspect_alignments(self.selected, answer)
            self.assertEqual(result["alignments"], [])

    def test_unsubstantiated_direct_source_to_implementation_transfer_is_rejected(self):
        answer = self._answer()
        answer["alignments"][0]["interpretation"] = (
            "This IoT pilot directly implements the academic lifecycle hypothesis from a distinct study.")
        result = inspect_alignments(self.selected, answer)
        self.assertEqual(result["alignments"], [])
        self.assertIn("direct cross-source", result["rejected_candidates"][0]["reason"])

    def test_missing_layer_must_be_disclosed(self):
        s=copy.deepcopy(self.selected)
        s["records"]=[r for r in s["records"] if r["layer"]!="practical"]
        a=self._answer()
        with self.assertRaisesRegex(ValueError,"missing evidence"):
            inspect_alignments(s,a)
        a["missing_layers"]=["practical"]
        a["alignments"][0]["practical_ids"]=[]
        result=inspect_alignments(s,a)
        self.assertFalse(result["alignments"][0]["complete_three_layer_stack"])

    def test_original_text_citations_are_source_exact_and_digest_verified(self):
        selected = copy.deepcopy(self.selected)
        corpus = {"schema": "cite_refinery.open_corpus.v1",
                  "material_type": "unclassified_source_records", "sources": []}
        for record in selected["records"]:
            text = "This is a specific bounded source excerpt about " + record["layer"] + " evidence and reported assumptions."
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            record["source_sha256"] = digest
            corpus["sources"].append({"id": record["id"], "url": record["source_url"],
                                      "sha256": digest, "text": text})
        grounded = attach_original_excerpts(selected, corpus)
        answer = self._answer()
        identifiers = {i for k in ("practical_ids", "academic_ids", "program_ids")
                       for i in answer["alignments"][0][k]}
        answer["alignments"][0]["citations"] = [
            {"source_id": ident, "quote": next(r["original_text"] for r in grounded["records"] if r["id"] == ident)}
            for ident in sorted(identifiers)]
        ok = inspect_alignments(grounded, answer)
        self.assertEqual(len(ok["alignments"]), 1)
        self.assertTrue(ok["alignments"][0]["source_text_checked"])
        self.assertEqual(len(ok["alignments"][0]["original_source_quotes"]), len(identifiers))
        answer["alignments"][0]["citations"][0]["quote"] = "An entirely invented quote about experimental impact."
        bad = inspect_alignments(grounded, answer)
        self.assertEqual(len(bad["alignments"]), 0)
        self.assertIn("quote not present", bad["rejected_candidates"][0]["reason"])
        corpus["sources"][0]["text"] = corpus["sources"][0]["text"]+" malicious mutation"
        with self.assertRaisesRegex(ValueError,"digest mismatch"):
            attach_original_excerpts(selected, corpus)

    def test_no_forced_alignment(self):
        result=inspect_alignments(self.selected, {"alignments":[],"missing_layers":[]})
        self.assertEqual(result["alignments"], [])
        self.assertEqual(result["rejected_candidates"], [])


if __name__ == "__main__":
    unittest.main()
