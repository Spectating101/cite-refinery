"""Integrity, coverage and authority boundaries for frozen source refreshes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.repository_layer import build_repository_layer, repository_layer_packet, validate_repository_layer
from cite_refinery.repository_layer_refresh import refresh_snapshot


class RepositoryRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.quote = "This program exports a versioned STEP solid with exact surfaces."
        self.digest = hashlib.sha256(self.quote.encode()).hexdigest()
        self.original = {"status": "captured", "source_url": "https://api.github.com/repos/old/part/git/blobs/" + "a" * 40,
                         "sha256": self.digest, "path": "/retained/README.source"}
        self.proof = {**self.original, "quote": self.quote, "start": 0, "end": len(self.quote)}
        self.record = {"cohort": "cohort-a", "catalog_id": "github:old/part", "status": "mapped",
                       "project": {"description": "Solid modelling", "topics": ["geometry"]},
                       "source": self.original, "source_sha256": self.digest,
                       "source_check": {"path": self.original["path"], "expected_sha256": self.digest,
                                        "actual_sha256": self.digest, "state": "match"},
                       "quote_checks": [{"source_path": self.original["path"], "source_sha256": self.digest,
                                         "quote_sha256": self.digest, "state": "match", "start_match": True, "end_match": True}],
                       "result_sha256": "b" * 64, "original_result_json_sha256": "b" * 64,
                       "result": {"source_sha256": self.digest, "purpose": "Export exact solids",
                                  "inputs": ["Geometry"], "outputs": ["STEP"], "analysis_method": "llm_source_review",
                                  "evidence": [self.proof], "contribution": "Sell a service"}}
        self.data = {"schema": "cite_refinery.repository_refresh_export.v1", "observed_at": "2026-11-19T09:00:00Z",
                     "records": [self.record], "stop": {"automatic_resume": False, "state": "stopped_at_user_request"}}

    def snapshot(self):
        path = self.root / "export.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        return refresh_snapshot(path)

    def catalog(self):
        snap = self.snapshot()
        path = self.root / "snapshot.json"
        path.write_text(json.dumps(snap), encoding="utf-8")
        return build_repository_layer([], supplemental_paths=[path])

    def test_acceptance_preserves_literal_evidence_and_does_not_promote_capability(self):
        catalog = self.catalog()
        self.assertTrue(validate_repository_layer(catalog)["valid"])
        self.assertEqual(catalog["coverage"]["source_mapping_status_counts"], {"mapped": 1})
        self.assertEqual(catalog["coverage"]["capability_count"], 0)
        self.assertEqual(catalog["repositories"][0]["source_interpretations"][0]["evidence"][0]["excerpt"], self.quote)
        self.assertNotIn("Sell a service", json.dumps(catalog))
        self.assertFalse(catalog["refresh"]["snapshots"][0]["stop"]["automatic_resume"])
        packet = repository_layer_packet(catalog)
        self.assertTrue(all(n["layer"] == "program" for n in packet["nodes"]))
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"] if e["relation"] == "HAS_SOURCE_INTERPRETATION"))

    def test_bad_hash_quote_or_offsets_excluded_with_reason_and_record_retained(self):
        for failure in ("source_hash", "quote", "offset", "result_hash"):
            with self.subTest(failure=failure):
                original = deepcopy(self.record)
                if failure == "source_hash":
                    self.record["source_check"]["actual_sha256"] = "0" * 64
                elif failure == "quote":
                    self.record["result"]["evidence"][0]["quote"] += " Forged tail."
                elif failure == "offset":
                    self.record["result"]["evidence"][0]["end"] += 1
                else:
                    self.record["result_sha256"] = "0" * 64
                snap = self.snapshot()
                self.assertEqual(len(snap["repositories"]), 1)
                self.assertEqual(snap["repositories"][0]["source_interpretations"], [])
                self.assertEqual(snap["refresh"]["excluded_accepted_interpretations"], 1)
                self.record.clear()
                self.record.update(original)

    def test_unreviewed_listings_remain_searchable_records(self):
        pending = deepcopy(self.record)
        pending.update(catalog_id="github:pending/review", cohort="cohort-b", status="ready", result=None,
                       source={"status": "source_unavailable"}, source_check=None, quote_checks=[])
        self.data["records"].append(pending)
        catalog = self.catalog()
        self.assertEqual(catalog["coverage"]["repository_count"], 2)
        self.assertEqual(catalog["coverage"]["source_mapping_status_counts"], {"mapped": 1, "ready": 1})

    def test_cross_repository_source_requires_reviewed_identity_and_preserves_listing(self):
        self.original["source_url"] = self.proof["source_url"] = "https://api.github.com/repos/new/part/git/blobs/" + "a" * 40
        self.assertEqual(self.snapshot()["refresh"]["admitted_interpretations"], 0)
        self.data["identity_reviews"] = [{"path": "/retained/identity-review.json", "sha256": "c" * 64,
            "document": {"groups": [{"canonical_id": "github:new/part", "catalog_ids": ["github:old/part"],
                                      "reason": "Reviewed redirect with captured original identity",
                                      "incumbent_bindings": {"github:old/part": {"node_id": "sgnode:old"}}}]}}]
        catalog = self.catalog()
        self.assertEqual(catalog["repositories"][0]["id"], "github:old/part")
        self.assertEqual(catalog["repositories"][0]["reviewed_identity"]["canonical_repository_id"], "github:new/part")
        self.assertEqual(catalog["coverage"]["source_interpretation_count"], 1)
        self.assertFalse(catalog["identity_resolutions"][0]["native_merge_performed"])
        self.assertNotIn("github:new/part", {n["key"] for n in repository_layer_packet(catalog)["nodes"]})

    def test_overlapping_cohorts_and_conflicting_identities_fail(self):
        self.data["records"].append(deepcopy(self.record))
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.snapshot()

    def test_gallery_is_accounted_without_turning_narratives_into_capabilities(self):
        self.data["gallery_records"] = [{"id": "gallery:one", "kind": "composition", "origin": "model",
            "original_payload_sha256": "d" * 64, "who": "A hypothetical customer", "buyer_validated": False}]
        snap = self.snapshot()
        self.assertEqual(snap["refresh"]["gallery_records_accounted"], 1)
        self.assertNotIn("buyer_validated", json.dumps(snap))
        self.assertEqual(snap["refresh"]["gallery_accounting"][0]["disposition"], "workflow_context_retained_separately")

    def test_census_decisions_keep_rejections_and_withheld_records_without_execution_claims(self):
        base = {"catalog_id": self.record["catalog_id"], "artifact": "step", "direction": "output",
                "source_path": self.original["path"], "source_sha256": self.digest,
                "source_url": self.original["source_url"], "census_evidence": {"quote": self.quote},
                "reason": "Reviewed project-owned STEP export statement", "interface_admission": "admit_verified_interface"}
        self.data["census_reviews"] = [{"sha256": "e" * 64, "document": {"reviews": [
            {**base, "review_id": "review:approved", "decision": "approve"},
            {**base, "review_id": "review:rejected", "decision": "reject", "reason": "Rejected attribution in this bounded fixture"},
            {**base, "review_id": "review:held", "decision": "restricted", "content_withheld": True},
        ]}}]
        catalog = self.catalog()
        self.assertEqual(catalog["coverage"]["technical_finding_status_counts"], {"approved": 1, "rejected": 1})
        self.assertEqual(catalog["coverage"]["capability_count"], 0)
        summary = catalog["refresh"]["snapshots"][0]
        self.assertEqual(summary["census_review_status_counts"], {"approved": 1, "held": 1, "rejected": 1})
        self.assertEqual(summary["exclusions"][0]["reason"], "withheld_content")
        self.assertTrue(all(e["status"] == "candidate" for e in repository_layer_packet(catalog)["edges"]
                            if e["relation"] == "HAS_SOURCE_REVIEW"))

    def test_format_only_pair_with_no_checked_endpoint_evidence_remains_excluded(self):
        self.data["handoff_documents"] = [{"document": {"representative_pairs": [{
            "id": "pair:one", "format": "step", "format_match_only": True,
            "producer": {"catalog_id": self.record["catalog_id"]},
            "consumer": {"catalog_id": self.record["catalog_id"]},
        }]}}]
        snap = self.snapshot()
        self.assertEqual(snap["proposed_relationships"], [])
        self.assertEqual(snap["refresh"]["handoff_examples_seen"], 1)
        self.assertEqual(snap["refresh"]["admitted_handoff_candidates"], 0)
        self.assertEqual(snap["refresh"]["exclusions"][0]["kind"], "technical_handoff_candidate")


if __name__ == "__main__":
    unittest.main()
