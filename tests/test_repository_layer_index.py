"""Authority-separated search, page evidence, and immutable SQLite publication."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.repository_layer import EVIDENCE_SCHEMA, build_repository_layer
from cite_refinery.repository_layer_index import build_repository_layer_index, query_repository_layer


class RepositoryLayerIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "technical.sqlite3"
        text = "Input streams are normalized into records."
        digest = hashlib.sha256(text.encode()).hexdigest()
        sources = [
            {"id": "source:alpha", "repository_id": "github:acme/alpha", "kind": "documentation",
             "url": "https://github.com/Acme/Alpha/blob/" + "a" * 40 + "/README.md",
             "path": "README.md", "revision": "a" * 40, "excerpt": "A bounded documented capability."},
            {"id": "source:beta", "repository_id": "github:acme/beta", "kind": "documentation",
             "url": "https://github.com/Acme/Beta/blob/" + "b" * 40 + "/README.md",
             "path": "README.md", "revision": "b" * 40, "excerpt": text,
             "capture_integrity": "match", "content_sha256": digest},
            {"id": "source:gamma", "repository_id": "github:acme/gamma", "kind": "metadata",
             "url": "https://github.com/Acme/Gamma", "excerpt": "Metadata alone is not a captured source document."},
            {"id": "source:gamma-failed", "repository_id": "github:acme/gamma", "kind": "documentation",
             "url": "https://github.com/Acme/Gamma", "excerpt": "A failed capture cannot establish source coverage.",
             "capture_integrity": "mismatch"},
        ]
        interpretation = {"purpose": "InterpretationNeedle normalizes incoming rows", "inputs": ["record_id, 100% literal"],
            "outputs": ["OutputOnlyNeedle"], "human_work": ["Choose the source fields"], "custom_glue": ["ConnectAdapterNeedle"],
            "limitations": ["Source review only"], "authority": "source_bound_model_interpretation",
            "analysis_method": "llm_source_review", "semantic_support_verified": False, "runtime_tested": False,
            "evidence": [{"source_id": "source:beta", "source_sha256": digest, "excerpt": text,
                          "byte_integrity_checked": True, "quote_integrity": "exact_quote_present",
                          "semantic_support_verified": False, "runtime_tested": False}]}
        snapshot = {"schema": "normalized_repository_snapshot", "repositories": [
            {"full_name": "Acme/Alpha", "description": "Documented transform", "domains": ["data"]},
            {"full_name": "Acme/Beta", "description": "Source reading", "domains": ["data"], "source_interpretations": [interpretation]},
            {"full_name": "Acme/Gamma", "domains": ["learning"], "proposed_capabilities": [
                {"key": "proposed", "name": "DoNotSearchLegacyNeedle", "mechanism": "ProposalOnlyNeedle",
                 "provenance": {"note": "RetainOriginalProvenanceNeedle"}}]},
            *[{"full_name": f"Inventory/Repo{i:03d}"} for i in range(72)],
        ], "sources": sources, "proposed_relationships": [{
            "id": "old-link", "source_repository_id": "github:acme/beta", "target_repository_id": "github:acme/gamma",
            "kind": "legacy_handoff", "original_relation": {"reason": "Shared format suggestion"}}]}
        self.snapshot = self.root / "snapshot.json"
        self.snapshot.write_text(json.dumps(snapshot), encoding="utf-8")
        evidence = {"schema": EVIDENCE_SCHEMA, "sources": [], "repositories": [{
            "repository_id": "github:acme/alpha", "capabilities": [{"key": "transform", "name": "Documented transformation",
                "mechanism": "CuratedMechanismNeedle transforms the documented input.", "inputs": [], "outputs": [],
                "requirements": [], "limitations": [], "evidence_level": "documented", "evidence_ids": ["source:alpha"]}]}],
            "relationships": [{"kind": "declared_dependency", "source_repository_id": "github:acme/alpha",
                "target_repository_id": "github:acme/beta", "description": "The cited document declares this dependency.",
                "evidence_ids": ["source:alpha"]}]}
        self.evidence = self.root / "evidence.json"
        self.evidence.write_text(json.dumps(evidence), encoding="utf-8")
        self.catalog = build_repository_layer([self.snapshot], evidence_path=self.evidence)
        self.receipt = build_repository_layer_index(self.catalog, self.path)

    def test_all_records_survive_pagination_and_authority_counts_remain_distinct(self):
        first = query_repository_layer(self.path)
        second = query_repository_layer(self.path, offset=30)
        third = query_repository_layer(self.path, offset=60)
        self.assertEqual([len(page["items"]) for page in (first, second, third)], [30, 30, 15])
        ids = [item["id"] for page in (first, second, third) for item in page["items"]]
        self.assertEqual(len(set(ids)), 75)
        self.assertEqual(set(ids), {item["id"] for item in self.catalog["repositories"]})
        self.assertEqual(first["coverage"], self.catalog["coverage"])
        self.assertEqual(first["coverage"]["source_interpreted_repository_count"], 1)
        self.assertEqual(first["coverage"]["reviewed_repository_count"], 1)
        self.assertEqual(first["coverage"]["source_captured_repository_count"], 2)
        self.assertEqual(query_repository_layer(self.path, offset=75)["items"], [])

    def test_technical_search_includes_interpretations_without_searching_legacy_proposals(self):
        for token in ("InterpretationNeedle", "OutputOnlyNeedle", "ConnectAdapterNeedle", "record_id", "%"):
            with self.subTest(token=token):
                result = query_repository_layer(self.path, query=token)
                self.assertEqual([item["id"] for item in result["items"]], ["github:acme/beta"])
        self.assertEqual(query_repository_layer(self.path, query="CuratedMechanismNeedle")["total"], 1)
        for token in ("DoNotSearchLegacyNeedle", "ProposalOnlyNeedle", "RetainOriginalProvenanceNeedle", "' OR 1=1 --"):
            with self.subTest(token=token):
                self.assertEqual(query_repository_layer(self.path, query=token)["total"], 0)
        gamma = query_repository_layer(self.path, query="github:acme/gamma")["items"][0]
        self.assertEqual(gamma, next(repo for repo in self.catalog["repositories"] if repo["id"] == gamma["id"]))

    def test_filters_do_not_promote_metadata_or_source_interpretations(self):
        self.assertEqual(query_repository_layer(self.path, domain="data")["total"], 2)
        expected = {"metadata_only": 74, "source_captured": 2, "source_interpreted": 1,
                    "documented": 1, "code_inspected": 0, "executed": 0, "partially_reviewed": 1}
        for state, count in expected.items():
            with self.subTest(state=state):
                self.assertEqual(query_repository_layer(self.path, review_state=state)["total"], count)
        self.assertEqual(query_repository_layer(self.path, domain="learning", review_state="source_captured")["total"], 0)

    def test_page_receipts_and_neighbors_follow_only_recorded_edges(self):
        alpha = query_repository_layer(self.path, query="github:acme/alpha", limit=1)
        self.assertEqual([source["id"] for source in alpha["sources"]], ["source:alpha"])
        self.assertEqual([neighbor["id"] for neighbor in alpha["neighbors"]], ["github:acme/beta"])
        self.assertEqual(len(alpha["relationships"]), 1)
        self.assertEqual(alpha["proposed_relationships"], [])
        beta = query_repository_layer(self.path, query="github:acme/beta")
        self.assertEqual({source["id"] for source in beta["sources"]}, {"source:alpha", "source:beta"})
        self.assertEqual({neighbor["id"] for neighbor in beta["neighbors"]}, {"github:acme/alpha", "github:acme/gamma"})
        self.assertEqual(len(beta["relationships"]), 1)
        self.assertEqual(len(beta["proposed_relationships"]), 1)
        blank = query_repository_layer(self.path, query="github:inventory/repo071")
        self.assertEqual(blank["relationships"], [])
        self.assertEqual(blank["proposed_relationships"], [])
        self.assertEqual(blank["neighbors"], [])

    def test_immutable_publication_reuses_exact_content_and_refuses_replacement(self):
        original = self.path.read_bytes()
        self.assertEqual(build_repository_layer_index(self.catalog, self.path), self.receipt)
        self.assertEqual(hashlib.sha256(original).hexdigest(), self.receipt["sha256"])
        snapshot = json.loads(self.snapshot.read_text())
        snapshot["repositories"][0]["description"] = "An updated observation"
        self.snapshot.write_text(json.dumps(snapshot), encoding="utf-8")
        changed = build_repository_layer([self.snapshot], evidence_path=self.evidence)
        with self.assertRaisesRegex(ValueError, "Immutable"):
            build_repository_layer_index(changed, self.path)
        self.assertEqual(self.path.read_bytes(), original)
        link = self.root / "symlink.sqlite3"
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            query_repository_layer(link)
        with self.assertRaises(ValueError):
            build_repository_layer_index(self.catalog, link)

    def test_invalid_parameters_and_unrecognized_databases_fail_closed(self):
        for arguments in ({"limit": 0}, {"limit": True}, {"offset": -1}, {"query": "x" * 251},
                          {"review_state": "workflow_explained"}, {"domain": "x" * 201}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                query_repository_layer(self.path, **arguments)
        other = self.root / "wrong.sqlite3"
        with sqlite3.connect(other) as connection:
            connection.execute("CREATE TABLE metadata(key TEXT,value TEXT)")
            connection.execute("INSERT INTO metadata VALUES('schema','\"not-this-index\"')")
        with self.assertRaisesRegex(ValueError, "schema"):
            query_repository_layer(other)
        invalid = deepcopy(self.catalog)
        invalid["scope"] = "mixed"
        with self.assertRaises(ValueError):
            build_repository_layer_index(invalid, self.root / "invalid.sqlite3")
        self.assertFalse((self.root / "invalid.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
