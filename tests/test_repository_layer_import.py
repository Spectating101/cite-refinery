"""Synthetic adapter contracts; these tests do not execute discovered software."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.repository_layer import build_repository_layer, repository_layer_packet, validate_repository_layer
from cite_refinery.repository_layer_import import connected_snapshot, current_catalog_snapshot, source_lock_snapshot


class RepositoryLayerImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.export = self.root / "current.json"
        self.normalized = self.root / "normalized.json"
        self.quote = "This parser accepts a JSON document and returns normalized records."
        self.source = {
            "source_url": "https://raw.githubusercontent.com/Example/Parser/main/README.md",
            "path": "/retained/capture/parser-readme.txt", "sha256": "a" * 64,
            "capture_integrity": "match", "kind": "readme", "byte_integrity_checked": True,
            "semantic_support_verified": False, "runtime_tested": False,
        }
        self.proof = {**self.source, "quote": self.quote, "start": 12, "end": 12 + len(self.quote),
                      "quote_integrity": "exact_quote_present"}
        self.interpretation = {
            "purpose": "Parse JSON records and normalize their fields.",
            "contribution": "Hypothetical market workflow that must not enter the repository layer.",
            "inputs": ["JSON records in the documented parser schema"],
            "outputs": ["Normalized JSON records"], "human_work": ["Select required fields"],
            "custom_glue": ["Adapt the caller to this parser schema"], "limits": ["No runtime trial was performed"],
            "evidence": [self.proof], "additional_evidence": [], "analysis_method": "llm_source_review",
            "explanation_state": "source_bound_model_interpretation", "status": "mapped", "worker": "source-review-worker",
            "semantic_support_verified": False, "runtime_tested": False,
            "workflow_families": ["hypothetical-business"], "workflow_roles": ["commercial-role"],
        }
        self.document = {
            "schema": "cite_refinery.current_repository_catalog_export.v1", "source_catalog_sha256": "b" * 64,
            "metadata": {"schema": "cite_refinery.software_discovery_catalog.v1", "built_at": "2026-11-18T00:00:00Z",
                         "coverage": {"total_projects": 3, "review_states": {"workflow_explained": 1, "metadata_only": 2}}},
            "integrity": {"source_checks": [{"path": self.source["path"], "expected_sha256": "a" * 64,
                                               "actual_sha256": "a" * 64, "state": "match"}],
                          "source_check_counts": {"match": 1}, "quote_check_counts": {"exact_quote_present": 1}},
            "projects": [
                {"catalog_id": "github:Example/Parser", "slug": "Example/Parser", "url": "https://github.com/Example/Parser",
                 "raw_payload_sha256": "c" * 64, "description": "JSON parser", "topics": ["data"],
                 "original_sources": [self.source], "source_interpretations": [self.interpretation],
                 "mapping_state": "mapped", "mapping_worker": "source-review-worker", "mapping_cohort_sha256": "d" * 64},
                {"catalog_id": "github:Second/Encoder", "slug": "Second/Encoder", "url": "https://github.com/Second/Encoder",
                 "raw_payload_sha256": "e" * 64, "description": "Also writes JSON", "topics": ["data"],
                 "original_sources": [], "source_interpretations": []},
                {"catalog_id": "product:example", "url": "https://example.test", "description": "Mentions https://github.com/Extra/Hidden"},
            ],
        }

    @staticmethod
    def write(path, data):
        path.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")

    def normalize(self):
        self.write(self.export, self.document)
        snapshot = current_catalog_snapshot(self.export)
        self.write(self.normalized, snapshot)
        return snapshot

    def test_current_complete_identity_union_and_source_interpretation_authority(self):
        snapshot = self.normalize()
        catalog = build_repository_layer([], supplemental_paths=[self.normalized])
        repos = {r["id"]: r for r in catalog["repositories"]}
        self.assertEqual(set(repos), {"github:example/parser", "github:second/encoder"})
        self.assertEqual(snapshot["import_summary"]["nonrepository_records"], 1)
        self.assertEqual(catalog["coverage"]["source_interpreted_repository_count"], 1)
        self.assertEqual(catalog["coverage"]["source_interpretation_count"], 1)
        self.assertEqual(catalog["coverage"]["capability_count"], 0)
        self.assertEqual(catalog["coverage"]["reviewed_repository_count"], 0)
        self.assertEqual(catalog["coverage"]["proposed_capability_count"], 0)
        interpreted = repos["github:example/parser"]["source_interpretations"][0]
        self.assertEqual(interpreted["authority"], "source_bound_model_interpretation")
        self.assertEqual(interpreted["inputs"], self.interpretation["inputs"])
        self.assertEqual(interpreted["limitations"], self.interpretation["limits"])
        self.assertFalse(interpreted["semantic_support_verified"])
        self.assertFalse(interpreted["runtime_tested"])
        self.assertEqual(interpreted["evidence"][0]["excerpt"], self.quote)
        serialized = json.dumps(catalog)
        self.assertNotIn(self.interpretation["contribution"], serialized)
        self.assertNotIn("hypothetical-business", serialized)
        self.assertNotIn("commercial-role", serialized)
        self.assertFalse(catalog["relationships"])
        packet = repository_layer_packet(catalog)
        self.assertTrue(all(n["layer"] == "program" for n in packet["nodes"]))
        self.assertFalse(any(n["kind"] == "capability" for n in packet["nodes"]))
        self.assertEqual(sum(n["kind"] == "source_interpretation" for n in packet["nodes"]), 1)
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"] if e["source"] == interpreted["id"] or e["target"] == interpreted["id"]))
        self.assertTrue(validate_repository_layer(catalog)["valid"])

    def test_source_hash_or_quote_failure_retains_inventory_without_interpretation(self):
        for failure in ("hash", "quote", "offset"):
            with self.subTest(failure=failure):
                doc = deepcopy(self.document)
                if failure == "hash":
                    doc["integrity"]["source_checks"][0].update(actual_sha256="f" * 64, state="mismatch")
                elif failure == "quote":
                    doc["projects"][0]["source_interpretations"][0]["evidence"][0]["quote_integrity"] = "unavailable_or_mismatch"
                else:
                    doc["projects"][0]["source_interpretations"][0]["evidence"][0]["end"] += 1
                self.write(self.export, doc)
                snapshot = current_catalog_snapshot(self.export)
                self.write(self.normalized, snapshot)
                catalog = build_repository_layer([], supplemental_paths=[self.normalized])
                self.assertEqual(catalog["coverage"]["repository_count"], 2)
                self.assertEqual(catalog["coverage"]["source_interpretation_count"], 0)
                self.assertEqual(snapshot["import_summary"]["unbound_interpretation_count"], 1)
                if failure == "hash":
                    self.assertEqual(catalog["coverage"]["source_captured_repository_count"], 0)

    def test_snapshot_completeness_and_source_identity_are_required(self):
        for failure in ("count", "payload", "repo_url", "source_owner", "false_hash_match"):
            with self.subTest(failure=failure):
                doc = deepcopy(self.document)
                if failure == "count":
                    doc["metadata"]["coverage"]["total_projects"] += 1
                elif failure == "payload":
                    del doc["projects"][0]["raw_payload_sha256"]
                elif failure == "repo_url":
                    doc["projects"][0]["url"] = "https://github.com/Other/Parser"
                elif failure == "source_owner":
                    doc["projects"][0]["original_sources"][0]["source_url"] = "https://raw.githubusercontent.com/Other/Parser/main/README.md"
                else:
                    doc["integrity"]["source_checks"][0]["actual_sha256"] = "f" * 64
                self.write(self.export, doc)
                with self.assertRaises(ValueError):
                    current_catalog_snapshot(self.export)

    def test_new_snapshot_preserves_history_without_duplicate_interpretation(self):
        first = self.normalize()
        first_path = self.root / "first.json"
        self.write(first_path, first)
        self.document["metadata"]["built_at"] = "2026-11-19T00:00:00Z"
        self.document["source_catalog_sha256"] = "f" * 64
        self.normalize()
        catalog = build_repository_layer([], supplemental_paths=[first_path, self.normalized, first_path])
        repo = next(r for r in catalog["repositories"] if r["id"] == "github:example/parser")
        self.assertEqual(len(catalog["sources"]), 1)
        self.assertEqual(len(repo["observations"]), 2)
        self.assertEqual(len(repo["source_interpretations"]), 1)
        self.assertEqual(len(repo["source_interpretations"][0]["provenance"]["observations"]), 2)
        self.assertEqual(repo["source_interpretations"][0]["id"], build_repository_layer([], supplemental_paths=[first_path])["repositories"][0]["source_interpretations"][0]["id"])

    def test_model_and_manual_source_interpretations_keep_distinct_labels(self):
        self.interpretation.pop("analysis_method")
        self.interpretation.pop("explanation_state")
        self.normalize()
        catalog = build_repository_layer([], supplemental_paths=[self.normalized])
        self.assertEqual(catalog["repositories"][0]["source_interpretations"][0]["authority"], "source_bound_interpretation")
        catalog["repositories"][0]["source_interpretations"][0]["semantic_support_verified"] = True
        with self.assertRaisesRegex(ValueError, "semantic or runtime"):
            validate_repository_layer(catalog)

    def test_connected_audit_is_bound_to_exact_snapshot_and_roles_remain_proposals(self):
        path, audit_path = self.root / "profiles.json", self.root / "audit.json"
        profiles = {"profiles": [
            {"id": "github:Example/Parser", "url": "https://github.com/Example/Parser", "roles": [{"role": "compiler", "title": "Unreviewed compiler"}]},
            {"id": "paper:example", "description": "Mentions https://github.com/Extra/Hidden"},
        ]}
        self.write(path, profiles)
        self.write(audit_path, {"profile_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        snapshot = connected_snapshot(path, audit_path)
        self.assertEqual(len(snapshot["repositories"]), 1)
        self.assertEqual(snapshot["repositories"][0]["proposed_capabilities"][0]["status"], "unreviewed")
        self.write(path, {"profiles": []})
        with self.assertRaisesRegex(ValueError, "different profile"):
            connected_snapshot(path, audit_path)

    def test_source_lock_preserves_multiple_file_observations_and_blob_identity(self):
        path = self.root / "lock.json"
        self.write(path, {"sources": [{"repository": "Example/Parser", "file_path": p, "captured_blob_sha": str(i) * 40}
                                      for i, p in enumerate(("README.md", "pyproject.toml"), 1)]})
        snapshot = source_lock_snapshot(path)
        self.assertEqual(len(snapshot["repositories"]), 2)
        self.assertEqual(len(snapshot["sources"]), 2)
        self.assertTrue(all(s["kind"] == "metadata" and "revision" not in s for s in snapshot["sources"]))


if __name__ == "__main__":
    unittest.main()
