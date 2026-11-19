"""Adversarial custody and endpoint-binding checks for completed findings."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.repository_layer import _digest, build_repository_layer, repository_layer_packet, validate_repository_layer
from cite_refinery.repository_layer_refresh import refresh_snapshot


class RepositoryRefreshIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = {"schema": "cite_refinery.repository_refresh_export.v1",
                     "observed_at": "2026-11-19T09:00:00Z", "records": []}
        for identity, operation in (("producer/part", "exports"), ("consumer/part", "imports")):
            quote = f"This program {operation} an exact STEP solid using its documented geometry operation."
            digest = hashlib.sha256(quote.encode()).hexdigest()
            source = {"status": "captured", "source_url": f"https://api.github.com/repos/{identity}/git/blobs/" + "a" * 40,
                      "sha256": digest, "path": f"/retained/{identity}/README.source"}
            proof = {**source, "quote": quote, "start": 0, "end": len(quote)}
            self.data["records"].append({
                "cohort": "cohort-a", "catalog_id": "github:" + identity, "status": "mapped", "project": {},
                "source": source, "source_sha256": digest,
                "source_check": {"path": source["path"], "expected_sha256": digest, "actual_sha256": digest, "state": "match"},
                "quote_checks": [{"source_path": source["path"], "source_sha256": digest, "quote_sha256": digest,
                                  "state": "match", "start_match": True, "end_match": True}],
                "result_sha256": "b" * 64, "original_result_json_sha256": "b" * 64,
                "result": {"source_sha256": digest, "purpose": operation + " exact geometry", "analysis_method": "llm_source_review",
                           "inputs": ["Geometry"], "outputs": ["Geometry"], "evidence": [proof]},
            })
        producer, consumer = self.data["records"]
        self.data["handoff_documents"] = [{"document": {"representative_pairs": [{
            "id": "pair:measured-contract", "format": "step", "format_match_only": True,
            "content_compatibility": "not_established", "required_checks": ["Versioned geometry fixtures remain unexecuted"],
            "producer": {"catalog_id": producer["catalog_id"], "purpose": "Export exact solid", "interface_evidence": producer["result"]["evidence"][0]},
            "consumer": {"catalog_id": consumer["catalog_id"], "purpose": "Read exact solid", "interface_evidence": consumer["result"]["evidence"][0]},
        }]}}]

    def snapshot(self):
        path = self.root / "export.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        return refresh_snapshot(path)

    def build(self, snapshot=None):
        path = self.root / "snapshot.json"
        path.write_text(json.dumps(snapshot if snapshot is not None else self.snapshot()), encoding="utf-8")
        return build_repository_layer([], supplemental_paths=[path])

    def test_missing_offset_attestations_cannot_become_verified_positions(self):
        for check in self.data["records"][0]["quote_checks"]:
            check.pop("start_match")
            check.pop("end_match")
        snapshot = self.snapshot()
        producer = next(row for row in snapshot["repositories"] if row["id"] == "github:producer/part")
        self.assertFalse(producer["source_interpretations"])
        self.assertEqual(snapshot["refresh"]["excluded_accepted_interpretations"], 1)
        self.assertEqual(snapshot["refresh"]["admitted_handoff_candidates"], 0)
        self.assertTrue(any("offset" in e["reason"] for e in snapshot["refresh"]["exclusions"]))

    def test_swapped_endpoint_evidence_fails_even_with_both_top_level_sources(self):
        snapshot = self.snapshot()
        candidate = snapshot["proposed_relationships"][0]
        producer = candidate["producer_contract"]
        consumer = candidate["consumer_contract"]
        producer["evidence"], consumer["evidence"] = consumer["evidence"], producer["evidence"]
        producer["evidence_ids"], consumer["evidence_ids"] = consumer["evidence_ids"], producer["evidence_ids"]
        self.assertEqual(len(candidate["evidence_ids"]), 2)
        with self.assertRaisesRegex(ValueError, "own repository"):
            self.build(snapshot)

    def test_non_contract_text_cannot_satisfy_a_technical_handoff(self):
        for malformed in ("exports STEP", ["exports STEP"], {"name": "Output", "format": "STEP"}):
            with self.subTest(contract=malformed):
                snapshot = self.snapshot()
                snapshot["proposed_relationships"][0]["producer_contract"] = malformed
                with self.assertRaisesRegex(ValueError, "contracts require"):
                    self.build(snapshot)

    def test_contract_evidence_cannot_be_hidden_from_candidate_sources(self):
        snapshot = self.snapshot()
        candidate = snapshot["proposed_relationships"][0]
        candidate["evidence_ids"] = candidate["producer_contract"]["evidence_ids"]
        with self.assertRaisesRegex(ValueError, "omit a contract"):
            self.build(snapshot)

    def test_source_candidate_cannot_claim_executed_authority(self):
        snapshot = self.snapshot()
        snapshot["proposed_relationships"][0]["runtime_tested"] = True
        with self.assertRaisesRegex(ValueError, "candidate requires"):
            self.build(snapshot)

    def test_rejected_technical_candidate_is_retained_without_active_graph_edge(self):
        snapshot = self.snapshot()
        snapshot["proposed_relationships"][0]["status"] = "rejected"
        catalog = self.build(snapshot)
        self.assertEqual(catalog["proposed_relationships"][0]["status"], "rejected")
        self.assertEqual(catalog["coverage"]["rejected_relationship_proposal_count"], 1)
        packet = repository_layer_packet(catalog)
        self.assertFalse(any(edge["relation"] == "PROPOSED_HANDOFF" for edge in packet["edges"]))

    def test_forged_identity_annotation_fails_even_after_rehashing_catalogue(self):
        document = {"groups": [{"canonical_id": "github:current/part", "catalog_ids": ["github:producer/part"],
                                "reason": "Fixture retained redirect review"}]}
        self.data["identity_reviews"] = [{"path": "/retained/review.json", "sha256": "c" * 64,
                                          "document": document, "exported_document_sha256": _digest(document)}]
        catalog = self.build()
        self.assertTrue(validate_repository_layer(catalog)["valid"])
        forged = deepcopy(catalog)
        producer = next(row for row in forged["repositories"] if row["id"] == "github:producer/part")
        producer["reviewed_identity"]["canonical_repository_id"] = "github:forged/part"
        forged["catalog_digest"] = _digest({k: v for k, v in forged.items() if k != "catalog_digest"})
        with self.assertRaisesRegex(ValueError, "identity annotation differs"):
            validate_repository_layer(forged)


if __name__ == "__main__":
    unittest.main()
