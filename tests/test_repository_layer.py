"""Repository-layer coverage, evidence authority and native-graph contracts."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.app import CiteRefinery
from cite_refinery.repository_layer import (
    EVIDENCE_SCHEMA,
    build_repository_layer,
    repository_layer_packet,
    validate_repository_layer,
)
from cite_refinery.semantic import SemanticGraph


class RepositoryLayerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.first = self.root / "first.json"
        self.second = self.root / "second.json"
        self.supplemental = self.root / "recovered.json"
        self.evidence_path = self.root / "reviewed.json"
        self.write(self.first, {
            "schema": "cite_refinery.opportunity_atlas_github_snapshot.v1",
            "observed_at": "2026-10-01T00:00:00Z",
            "repositories": [
                {"full_name": "Alpha/Zip", "description": "Archive splitter", "language": "Python",
                 "found_in": ["archives"], "topics": ["zip"], "buyer_demand": "unknown"},
                {"full_name": "Beta/Core", "description": "Metadata normalization", "found_in": ["data"], "language": "Rust"},
                {"full_name": "Learn/Tutorial", "description": "Tutorials, not a compiler", "found_in": ["learning"]},
            ],
        })
        self.write(self.second, {
            "schema": "cite_refinery.opportunity_atlas_github_snapshot.v1",
            "observed_at": "2026-11-01T00:00:00Z",
            "repositories": [
                {"full_name": "alpha/ZIP", "description": "Split large ZIP archives", "language": "Python",
                 "found_in": ["storage"], "topics": ["archives"], "commercial_status": "unknown"},
                {"full_name": "Gamma/Editor", "description": "Structured file editor", "found_in": ["editing"]},
            ],
        })
        self.recovered = {
            "schema": "normalized_repository_snapshot",
            "observed_at": "2026-11-18T00:00:00Z",
            "repositories": [
                {"id": "github:ALPHA/ZIP", "domains": ["utilities"], "proposed_capabilities": [
                    {"key": "printing", "name": "Prepare additive manufacturing jobs",
                     "rationale": "Legacy keyword interpretation of slicer"}]},
                {"id": "github:learn/tutorial", "proposed_capabilities": [
                    {"key": "compiler", "name": "Compile firmware", "rationale": "Tutorial mentions compiler installation"}]},
                {"id": "pypi:some-package", "description": "A package record is not a repository identity"},
            ],
            "sources": [{
                "id": "src:captured-zip", "repository_id": "github:alpha/zip",
                "url": "https://github.com/Alpha/Zip/blob/" + "1" * 40 + "/README.md",
                "revision": "1" * 40, "path": "README.md", "kind": "documentation",
                "excerpt": "This utility splits large ZIP archives.",
            }],
            "relationships": [],
            "proposed_relationships": [{
                "id": "legacy-edge-one", "source_repository_id": "github:alpha/zip",
                "target_repository_id": "github:beta/core", "type": "legacy_handoff",
                "original_relation": {"basis": "shared JSON format", "status": "compatible"},
                "provenance": {"snapshot": "connected-catalog-v2"},
            }],
        }
        self.write(self.supplemental, self.recovered)
        self.evidence = {
            "schema": EVIDENCE_SCHEMA,
            "sources": [self.source("zip", "alpha/zip"), self.source("core", "beta/core")],
            "repositories": [
                {"repository_id": "github:alpha/zip", "capabilities": [self.capability("archive_split", "Split ZIP archives", "zip")],
                 "rejected_assignments": [{"key": "printing", "name": "Prepare additive manufacturing jobs",
                    "reason": "The reviewed documentation concerns compressed archives; the printing assignment is unsupported.",
                    "evidence_ids": ["src:zip"]}]},
                {"repository_id": "github:beta/core", "capabilities": [self.capability("normalize", "Normalize metadata", "core")]},
            ],
            "relationships": [],
        }
        self.write(self.evidence_path, self.evidence)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def source(label, repository, kind="documentation"):
        return {"id": "src:" + label, "repository_id": "github:" + repository,
                "url": "https://github.com/" + repository + "/blob/" + "a" * 40 + "/README.md",
                "revision": "a" * 40, "path": "README.md", "kind": kind,
                "excerpt": "A bounded source excerpt for this contract test."}

    @staticmethod
    def capability(key, name, source):
        return {"key": key, "name": name, "mechanism": "Read structured input and perform the documented bounded operation.",
                "inputs": [{"name": "Record", "format": "JSON", "description": "Input object in the documented schema", "evidence_ids": ["src:" + source]}],
                "outputs": [{"name": "Result", "format": "JSON", "description": "Output object in this component's schema", "evidence_ids": ["src:" + source]}],
                "requirements": [], "limitations": [{"text": "The quoted document does not establish execution performance.", "evidence_ids": ["src:" + source]}],
                "evidence_level": "documented", "evidence_ids": ["src:" + source]}

    def build(self, *, reviewed=True):
        return build_repository_layer([self.first, self.second], supplemental_paths=[self.supplemental],
                                      evidence_path=self.evidence_path if reviewed else None)

    def rewrite_evidence(self):
        self.write(self.evidence_path, self.evidence)

    def test_complete_case_insensitive_union_retains_domains_and_observations(self):
        catalog = self.build()
        repos = {r["id"]: r for r in catalog["repositories"]}
        self.assertEqual(set(repos), {"github:alpha/zip", "github:beta/core", "github:gamma/editor", "github:learn/tutorial"})
        zip_repo = repos["github:alpha/zip"]
        self.assertEqual(zip_repo["domains"], ["archives", "storage", "utilities"])
        self.assertEqual(zip_repo["topics"], ["archives", "zip"])
        self.assertEqual(len(zip_repo["observations"]), 3)
        self.assertIn("Alpha/Zip", zip_repo["aliases"])
        self.assertIn("alpha/ZIP", zip_repo["aliases"])
        self.assertEqual(zip_repo["description"], "Split large ZIP archives")
        self.assertEqual(catalog["coverage"]["repository_count"], 4)
        self.assertEqual(sum(s.get("nonrepository_records_excluded", 0) for s in catalog["input_sources"]), 1)

    def test_source_capture_and_legacy_roles_do_not_establish_capabilities(self):
        catalog = self.build(reviewed=False)
        self.assertEqual(catalog["coverage"]["source_captured_repository_count"], 1)
        self.assertEqual(catalog["coverage"]["capability_count"], 0)
        self.assertEqual(catalog["coverage"]["reviewed_repository_count"], 0)
        self.assertEqual(catalog["coverage"]["proposed_capability_count"], 2)
        self.assertTrue(all(r["review_state"] == "unreviewed" for r in catalog["repositories"]))
        self.assertTrue(all("capabilities" in r["unknowns"] for r in catalog["repositories"]))

    def test_technical_hints_and_domain_judgments_remain_metadata(self):
        self.recovered["repositories"][1]["technical_context"] = {
            "source_state": "captured", "known_functions": ["a compiler is discussed in a tutorial"],
            "documented_interface_hints": ["mentions JSON"], "mapping_method": "keyword proposal",
        }
        self.recovered["repositories"][1]["domain_judgments"] = [{
            "domain_id": "learning", "label": "different_meaning", "reason": "Tutorial references are not compiler implementation.",
        }]
        self.write(self.supplemental, self.recovered)
        repo = next(r for r in self.build()["repositories"] if r["id"] == "github:learn/tutorial")
        self.assertEqual(repo["capabilities"], [])
        self.assertIn("learning", repo["domains"])
        self.assertEqual(repo["domain_judgments"][0]["authority"], "metadata_only")
        hints = next(o["technical_context"] for o in repo["observations"] if "technical_context" in o)
        self.assertEqual(hints["documented_interface_hints"], ["mentions JSON"])

    def test_wrong_role_is_rejected_without_erasing_its_history(self):
        catalog = self.build()
        repo = next(r for r in catalog["repositories"] if r["id"] == "github:alpha/zip")
        self.assertEqual([c["key"] for c in repo["capabilities"]], ["archive_split"])
        self.assertEqual(repo["proposed_capabilities"][0]["status"], "rejected")
        self.assertIn("Legacy keyword interpretation", repo["proposed_capabilities"][0]["mechanism"])
        self.assertEqual(catalog["coverage"]["rejected_assignment_count"], 1)
        self.assertEqual(catalog["coverage"]["rejected_proposal_count"], 1)
        self.assertIn("archive_split.requirements", repo["unknowns"])

    def test_deterministic_rebuild_order_and_stable_record_ids(self):
        first = self.build()
        self.assertEqual(first, self.build())
        reverse = build_repository_layer([self.second, self.first], supplemental_paths=[self.supplemental], evidence_path=self.evidence_path)
        self.assertEqual(first, reverse)
        self.evidence["repositories"][0]["capabilities"][0]["mechanism"] += " A clarified explanation."
        self.rewrite_evidence()
        updated = self.build()
        self.assertEqual([r["id"] for r in first["repositories"]], [r["id"] for r in updated["repositories"]])
        self.assertEqual(first["repositories"][0]["capabilities"][0]["id"], updated["repositories"][0]["capabilities"][0]["id"])
        self.assertNotEqual(first["catalog_digest"], updated["catalog_digest"])

    def test_metadata_cannot_be_relabelled_documented_or_executed(self):
        original = deepcopy(self.evidence)
        cases = (("metadata", "documented"), ("documentation", "code_inspected"), ("documentation", "executed"), ("execution", "executed"))
        for kind, level in cases:
            with self.subTest(kind=kind, level=level):
                self.evidence = deepcopy(original)
                self.evidence["sources"][0]["kind"] = kind
                self.evidence["repositories"][0]["capabilities"][0]["evidence_level"] = level
                self.rewrite_evidence()
                with self.assertRaises(ValueError):
                    self.build()

    def test_missing_source_and_conflicting_source_identity_fail(self):
        self.evidence["repositories"][0]["capabilities"][0]["evidence_ids"] = ["src:invented"]
        self.rewrite_evidence()
        with self.assertRaisesRegex(ValueError, "unknown source"):
            self.build()
        self.evidence["repositories"][0]["capabilities"][0]["evidence_ids"] = ["src:zip"]
        source = deepcopy(self.evidence["sources"][0])
        source["excerpt"] = "Conflicting record under same source identifier"
        self.evidence["sources"].append(source)
        self.rewrite_evidence()
        with self.assertRaisesRegex(ValueError, "conflicting records"):
            self.build()

    def test_shared_json_and_legacy_handoffs_create_no_active_connections(self):
        catalog = self.build()
        self.assertEqual(catalog["relationships"], [])
        self.assertEqual(catalog["coverage"]["relationship_count"], 0)
        self.assertEqual(catalog["coverage"]["proposed_relationship_count"], 1)
        proposed = catalog["proposed_relationships"][0]
        self.assertEqual(proposed["status"], "unreviewed")
        self.assertEqual(proposed["original_relation"]["status"], "compatible")
        packet = repository_layer_packet(catalog)
        self.assertFalse(any(e["relation"] in {"DEPENDS_ON", "PROPOSED_HANDOFF", "TESTED_HANDOFF"} for e in packet["edges"]))
        self.evidence["relationships"] = [{"kind": "proposed_handoff", "source_repository_id": "github:alpha/zip",
            "target_repository_id": "github:beta/core", "description": "Both use JSON", "basis": "shared_json", "evidence_ids": ["src:zip", "src:core"]}]
        self.rewrite_evidence()
        with self.assertRaisesRegex(ValueError, "shared format or topic"):
            self.build()

    def test_rejected_legacy_roles_invalidate_related_connection_proposals(self):
        handoff = self.recovered["proposed_relationships"][0]
        handoff["producer_role"] = "printing"
        comparison = deepcopy(handoff)
        comparison.update(id="legacy-comparison", type="legacy_comparison", source_role="printing")
        del comparison["producer_role"]
        self.recovered["proposed_relationships"].append(comparison)
        self.write(self.supplemental, self.recovered)
        catalog = self.build()
        self.assertEqual(len(catalog["proposed_relationships"]), 2)
        self.assertTrue(all(p["status"] == "rejected" for p in catalog["proposed_relationships"]))
        self.assertTrue(all("printing rejected" in p["rejection_reason"] for p in catalog["proposed_relationships"]))
        self.assertEqual(catalog["coverage"]["rejected_relationship_proposal_count"], 2)
        self.assertEqual(catalog["relationships"], [])

    def test_native_packet_contains_only_program_nodes_and_valid_endpoints(self):
        catalog = self.build()
        packet = repository_layer_packet(catalog, project_id="rproject:test")
        self.assertEqual({n["layer"] for n in packet["nodes"]}, {"program"})
        self.assertFalse(any(n["kind"] == "problem_claim" for n in packet["nodes"]))
        self.assertEqual(len([n for n in packet["nodes"] if n["kind"] == "repository"]), 4)
        self.assertEqual(len([n for n in packet["nodes"] if n["kind"] == "capability"]), 2)
        keys = [n["key"] for n in packet["nodes"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(e["source"] in keys and e["target"] in keys for e in packet["edges"]))
        rendered = json.dumps(catalog)
        self.assertNotIn('"buyer_demand"', rendered)
        self.assertNotIn('"commercial_status"', rendered)

    def test_native_import_is_idempotent_without_problem_bootstrap(self):
        app = CiteRefinery(self.root / "native-workspace")
        project = app.init_project("Repository inventory", "Repository inventory only")
        graph = SemanticGraph(app.store)
        packet = repository_layer_packet(self.build(), project.id)
        first = graph.ingest_packet(project.id, packet)
        before = graph.export(project.id)
        again = graph.ingest_packet(project.id, packet)
        after = graph.export(project.id)
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(before, after)
        self.assertFalse(any(n["kind"] == "problem_claim" for n in after["nodes"].values()))

    def test_later_snapshot_adds_sources_without_erasing_existing_history(self):
        original = self.build()
        app = CiteRefinery(self.root / "evolving-native-workspace")
        project = app.init_project("Repository inventory", "Repository inventory only")
        graph = SemanticGraph(app.store)
        graph.ingest_packet(project.id, repository_layer_packet(original, project.id))
        before = graph.export(project.id)
        next_path = self.root / "next_snapshot.json"
        self.write(next_path, {"observed_at": "2026-11-19T00:00:00Z", "repositories": [
            {"full_name": "Alpha/ZIP", "description": "Updated documented archive operation", "found_in": ["compression"]},
            {"full_name": "Delta/Plugin", "description": "An additional known repository", "found_in": ["extensions"]},
        ]})
        updated_source = self.source("zip-next", "alpha/zip")
        updated_source.update(revision="b" * 40, excerpt="A later source revision adds a bounded documentation clarification.",
                              url="https://github.com/alpha/zip/blob/" + "b" * 40 + "/README.md")
        self.evidence["sources"].append(updated_source)
        self.evidence["repositories"][0]["capabilities"][0]["evidence_ids"].append("src:zip-next")
        self.rewrite_evidence()
        updated = build_repository_layer([self.first, self.second, next_path], supplemental_paths=[self.supplemental], evidence_path=self.evidence_path)
        self.assertEqual(updated["coverage"]["repository_count"], 5)
        old_zip = next(r for r in original["repositories"] if r["id"] == "github:alpha/zip")
        new_zip = next(r for r in updated["repositories"] if r["id"] == "github:alpha/zip")
        self.assertTrue(set(old_zip["aliases"]).issubset(new_zip["aliases"]))
        self.assertTrue({o["record_sha256"] for o in old_zip["observations"]}.issubset({o["record_sha256"] for o in new_zip["observations"]}))
        self.assertTrue({s["id"] for s in original["sources"]}.issubset({s["id"] for s in updated["sources"]}))
        packet = repository_layer_packet(updated, project.id)
        graph.ingest_packet(project.id, packet)
        after = graph.export(project.id)
        self.assertTrue(set(before["nodes"]).issubset(after["nodes"]))
        self.assertEqual(len([n for n in after["nodes"].values() if n["kind"] == "repository"]), 5)
        graph.ingest_packet(project.id, packet)
        self.assertEqual(after, graph.export(project.id))

    def test_dependency_proposed_and_tested_relations_keep_distinct_authority(self):
        self.evidence["sources"].append(self.source("execution", "gamma/editor", "execution"))
        self.evidence["relationships"] = [
            {"kind": "declared_dependency", "source_repository_id": "github:alpha/zip", "target_repository_id": "github:beta/core",
             "description": "A documented optional backend; availability does not prove compatibility", "scope": {"required": False, "dependency_type": "optional_backend"}, "evidence_ids": ["src:zip"]},
            {"kind": "proposed_handoff", "source_repository_id": "github:beta/core", "target_repository_id": "github:gamma/editor",
             "description": "A reviewed proposal requiring an explicit schema adapter", "evidence_ids": ["src:core"]},
            {"kind": "tested_handoff", "source_repository_id": "github:alpha/zip", "target_repository_id": "github:beta/core",
             "source_capability_key": "archive_split", "target_capability_key": "normalize",
             "description": "Only the exact fixture interchange was executed", "evidence_ids": ["src:execution"],
             "scope": {"source_revision": "a" * 40, "target_revision": "b" * 40, "case": "one bounded fixture", "result": "pass"}},
        ]
        self.rewrite_evidence()
        catalog = self.build()
        self.assertEqual(catalog["coverage"]["relationship_count"], 3)
        edges = {e["relation"]: e for e in repository_layer_packet(catalog)["edges"] if e["relation"] in {"DEPENDS_ON", "PROPOSED_HANDOFF", "TESTED_HANDOFF"}}
        self.assertEqual(edges["PROPOSED_HANDOFF"]["status"], "candidate")
        self.assertEqual(edges["TESTED_HANDOFF"]["provenance"]["technical_relationship"]["scope"]["case"], "one bounded fixture")
        self.evidence["relationships"][-1]["scope"]["result"] = "fail"
        self.rewrite_evidence()
        with self.assertRaisesRegex(ValueError, "successful execution"):
            self.build()

    def test_failed_and_blocked_evidence_is_preserved_without_success_promotion(self):
        source = self.source("negative", "alpha/zip", "execution")
        source["cases"] = [{"name": "broken case", "status": "fail"}, {"name": "hardware", "status": "blocked"}]
        self.evidence["sources"].append(source)
        self.evidence["repositories"][0]["capabilities"][0]["limitations"].append({"text": "One tested case fails; hardware validation was blocked.", "evidence_ids": ["src:negative"]})
        self.rewrite_evidence()
        catalog = self.build()
        recorded = next(s for s in catalog["sources"] if s["id"] == "src:negative")
        self.assertEqual([c["status"] for c in recorded["cases"]], ["fail", "blocked"])
        self.assertEqual(catalog["coverage"]["evidence_levels"]["executed"], 0)
        self.assertEqual(catalog["relationships"], [])

    def test_validator_rejects_contamination_tampering_and_rejected_active_role(self):
        catalog = self.build()
        bad = deepcopy(catalog)
        bad["problems"] = [{"name": "not this layer"}]
        with self.assertRaisesRegex(ValueError, "demand-layer"):
            validate_repository_layer(bad)
        bad = deepcopy(catalog)
        bad["repositories"][0]["description"] = "Changed after catalog build"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            validate_repository_layer(bad)
        self.evidence["repositories"][0]["capabilities"][0]["key"] = "printing"
        self.rewrite_evidence()
        with self.assertRaisesRegex(ValueError, "rejected assignment remains"):
            self.build()

    def test_relationship_endpoints_and_capabilities_must_exist(self):
        relation = {"kind": "declared_dependency", "source_repository_id": "github:alpha/zip",
                    "target_repository_id": "github:unknown/repo", "description": "An invalid endpoint fixture", "evidence_ids": ["src:zip"]}
        self.evidence["relationships"] = [relation]
        self.rewrite_evidence()
        with self.assertRaisesRegex(ValueError, "unknown repository"):
            self.build()
        relation["target_repository_id"] = "github:learn/tutorial"
        relation["target_capability_key"] = "compiler"
        self.rewrite_evidence()
        with self.assertRaisesRegex(ValueError, "unreviewed or unknown capability"):
            self.build()


if __name__ == "__main__":
    unittest.main()
