"""Academic source-depth map: frozen development-only provenance and bounded reviews."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.academic_evidence_atlas import (
    build_academic_atlas, balanced_review_queue, browse_academic,
    load_review_source_texts,
)
from cite_refinery.layered_cli import main as canonical_cli

BASE = Path(__file__).resolve().parents[1]
CORPUS = BASE / "research_materials/runtime_trials/richer_corpus_20261020"


def digest(value):
    return sha256(value.encode("utf-8")).hexdigest()


def specimen():
    a = "Intro. " + "Researchers recorded methods across fictional clinics. "*9
    b = "Intro. " + "Fictional controlled groups had differing observed outcomes. "*9
    d = "Metadata listing only; files have not been opened."
    records = [
        ("PMC-demo-a", "https://europepmc.org/articles/PMC12345", a, "full_text_jats"),
        ("PMC-demo-b", "https://europepmc.org/articles/PMC56789", b, "full_text_jats"),
        ("ZEN-demo-c", "https://zenodo.org/records/919191", d, "dataset_metadata"),
    ]
    docs = [{
        "id": sid, "canonical_url": url, "title": "Fictional "+sid,
        "type": kind, "text_sha256": digest(body),
        "word_count": len(body.split()), "document_date": "2026-04-01",
        "source_scope": "Fictional source fixture only",
    } for sid, url, body, kind in records]
    manifest = {
        "schema": "cite_refinery.richer_development_manifest.v1",
        "documents": docs, "development_source_count": 3,
        "map_ready_source_count": 3,
        "material_by_type": {"full_text_jats": 2, "dataset_metadata": 1},
        "scientific_truth_validated": False, "heldout_source_records_exposed": 0,
        "model_given_collection_quota_labels": False,
    }
    split = {
        "schema": "cite_refinery.richer_corpus_public_manifest.v1",
        "development_count": 3, "holdout_count": 2,
        "eligible_new_materials": 5,
        "development_type_counts": {"full_text_jats": 2, "dataset_metadata": 1},
        "holdout_status": "sealed_not_mapped_not_reviewed",
        "accuracy_scores_available": False,
        "holdout_seal_sha256": "a"*64, "source_fingerprint_sha256": "b"*64,
    }
    quote_a = "Researchers recorded methods across fictional clinics."
    quote_b = "Fictional controlled groups had differing observed outcomes."
    claims = [{
        "id": "claim-a", "source_id": "PMC-demo-a",
        "start": a.index(quote_a), "end": a.index(quote_a)+len(quote_a),
        "quote": quote_a, "statement": "Authors describe their observations.",
        "role": "method", "review_state": "analyst_source_span_checked",
        "reviewer": "fictional-reviewer", "reviewed_at": "2026-10-21",
        "scope": {"population": "fictional clinic participants", "setting": "fictional clinic",
                  "outcome": "data recording", "study_design": "operator-described method"},
    }, {
        "id": "claim-b", "source_id": "PMC-demo-b",
        "start": b.index(quote_b), "end": b.index(quote_b)+len(quote_b),
        "quote": quote_b, "statement": "Authors report differing values.",
        "role": "result", "review_state": "candidate",
        "scope": {"population": "fictional control sample", "setting": "fictional clinic",
                  "outcome": "difference", "study_design": "unspecified author report"},
    }]
    review = {
        "schema": "cite_refinery.academic_evidence_reviews.v1",
        "claims": claims,
        "tensions": [{
            "id": "tension-1", "claim_ids": ["claim-a","claim-b"],
            "comparison_question": "Are these two fictional records methodologically comparable?"
        }],
    }
    return manifest, split, review, {"PMC-demo-a": a, "PMC-demo-b": b}


class AcademicEvidenceAtlasTests(unittest.TestCase):
    def test_existing_103_source_development_partition_and_66_sealed_holdout(self):
        manifest = json.loads((CORPUS/"development_source_manifest.json").read_text())
        split = json.loads((CORPUS/"frozen_split_receipt.json").read_text())
        atlas = build_academic_atlas(manifest, split)
        self.assertEqual(atlas["coverage"]["development_documents"], 103)
        self.assertEqual(atlas["coverage"]["indexed_article_fulltexts"], 43)
        self.assertEqual(atlas["coverage"]["indexed_institutional_reports"], 31)
        self.assertEqual(atlas["coverage"]["dataset_metadata_records_not_observations"], 29)
        self.assertEqual(atlas["coverage"]["sealed_holdout_documents_not_imported"], 66)
        self.assertEqual(atlas["coverage"]["mapper_ready_development_documents"], 101)
        self.assertEqual(atlas["coverage"]["source_anchored_claims"], 0)
        self.assertFalse(atlas["coverage"]["world_field_coverage_proven"])
        self.assertFalse(atlas["provenance"]["heldout_source_id_or_text_imported"])
        self.assertEqual(len(balanced_review_queue(atlas)["entries"]), 30)
        self.assertEqual(browse_academic(atlas,genre="full_text_jats")["matching_count"],43)
        self.assertGreater(browse_academic(atlas,terms="sensor")["matching_count"],0)
        self.assertFalse(browse_academic(atlas)["not_quality_ranked"] is False)

    def test_source_spans_methods_and_tensions_are_not_scientific_proof(self):
        m,s,r,texts=specimen()
        atlas=build_academic_atlas(m,s,reviews=r,source_texts=texts)
        self.assertEqual(atlas["coverage"]["source_anchored_claims"],2)
        self.assertEqual(atlas["coverage"]["sources_with_anchored_claims"],2)
        self.assertEqual(atlas["coverage"]["candidate_scope_tensions"],1)
        self.assertEqual(atlas["coverage"]["confirmed_scientific_contradictions"],0)
        self.assertEqual(atlas["coverage"]["independently_validated_scientific_findings"],0)
        self.assertTrue(atlas["claims"]["claim-a"]["exact_span_matches_frozen_extracted_text"])
        self.assertFalse(atlas["claims"]["claim-b"]["publisher_claim_verified_or_replicated"])
        self.assertNotIn("quote", atlas["claims"]["claim-a"])
        self.assertNotIn("text", atlas["sources"]["PMC-demo-a"])
        self.assertEqual(browse_academic(atlas,terms="observations")["matching_count"],1)
        self.assertTrue(atlas["tensions"]["tension-1"]["state"].startswith("candidate_"))
        self.assertEqual(balanced_review_queue(atlas)["total_items"],1)

    def test_forged_quote_digest_role_and_duplicate_rejected(self):
        m,s,r,texts=specimen()
        bad=deepcopy(r)
        bad["claims"][0]["quote"]="Fabricated sentence not in the paper at all."
        with self.assertRaisesRegex(ValueError,"exact bounded source"):
            build_academic_atlas(m,s,reviews=bad,source_texts=texts)
        wrong=dict(texts)
        wrong["PMC-demo-a"]="tampered"
        with self.assertRaisesRegex(ValueError,"frozen extracted-text"):
            build_academic_atlas(m,s,reviews=r,source_texts=wrong)
        bad=deepcopy(r)
        bad["claims"][0]["role"]="causally_proven"
        with self.assertRaisesRegex(ValueError,"role"):
            build_academic_atlas(m,s,reviews=bad,source_texts=texts)
        bad=deepcopy(r)
        bad["claims"].append(deepcopy(bad["claims"][0]))
        bad["claims"][-1]["id"]="same-span-repeated"
        with self.assertRaisesRegex(ValueError,"Repeated source span"):
            build_academic_atlas(m,s,reviews=bad,source_texts=texts)

    def test_dataset_metadata_cannot_supply_an_academic_finding(self):
        m,s,r,texts=specimen()
        text="Metadata listing only; files have not been opened."
        bad=deepcopy(r)
        bad["claims"][0].update(
            source_id="ZEN-demo-c",start=0,end=len(text),quote=text)
        with self.assertRaisesRegex(ValueError,"Dataset metadata"):
            build_academic_atlas(m,s,reviews=bad,
                                source_texts={**texts,"ZEN-demo-c":text})

    def test_source_disagreements_are_not_created_from_same_article(self):
        m,s,r,texts=specimen()
        r["tensions"][0]["claim_ids"]=["claim-a","claim-a"]
        with self.assertRaisesRegex(ValueError,"two distinct"):
            build_academic_atlas(m,s,reviews=r,source_texts=texts)

    def test_holdout_and_duplicate_source_and_identity_tampering_rejected(self):
        m,s,r,texts=specimen()
        bad=deepcopy(m)
        bad["documents"][0]["collection_quota"]="s10"
        with self.assertRaisesRegex(ValueError,"restricted"):
            build_academic_atlas(bad,s)
        bad=deepcopy(m)
        bad["documents"][1]["canonical_url"]=bad["documents"][0]["canonical_url"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            build_academic_atlas(bad,s)
        bad=deepcopy(s)
        bad["holdout_status"]="read_by_mapper"
        with self.assertRaisesRegex(ValueError,"frozen"):
            build_academic_atlas(m,bad)
        bad=deepcopy(s)
        bad["development_count"]=4
        with self.assertRaises(ValueError):
            build_academic_atlas(m,bad)

    def test_local_original_text_only_explicit_file_and_no_symlink(self):
        m,s,r,texts=specimen()
        with TemporaryDirectory() as td:
            root=Path(td)
            (root/"PMC-demo-a.txt").write_text(texts["PMC-demo-a"],encoding="utf-8")
            assert load_review_source_texts(root,["PMC-demo-a"])=={
                "PMC-demo-a":texts["PMC-demo-a"]}
            with self.assertRaises(ValueError):
                load_review_source_texts(root,["../private"])
            (root/"PMC-demo-a.txt").unlink()
            (root/"PMC-demo-a.txt").symlink_to(root/"private.txt")
            with self.assertRaisesRegex(ValueError,"symlinked"):
                load_review_source_texts(root,["PMC-demo-a"])

    def test_existing_canonical_investigator_emits_standalone_academic_and_queue(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            result=canonical_cli([
                "investigate","map-foundations",
                "--academic-development-manifest",
                str(CORPUS/"development_source_manifest.json"),
                "--academic-split-receipt",str(CORPUS/"frozen_split_receipt.json"),
                "--academic-genre","full_text_jats","--academic-terms","sensor",
                "--academic-atlas-out",str(root/"academic.json"),
                "--academic-review-backlog-out",str(root/"queue.json"),
                "--json-out",str(root/"all.json"),
                "--markdown-out",str(root/"all.md"),
            ])
            self.assertIn(result,(None,0))
            data=json.loads((root/"all.json").read_text())
            self.assertEqual(data["academic"]["development_evidence_atlas"]["coverage"][
                "indexed_article_fulltexts"],43)
            self.assertEqual(len(json.loads((root/"queue.json").read_text())["entries"]),30)
            self.assertFalse(data["academic"]["development_evidence_atlas"][
                "provenance"]["heldout_source_id_or_text_imported"])
            self.assertEqual(data["cross_layer_edges_generated"],0)


if __name__=="__main__":
    unittest.main()
