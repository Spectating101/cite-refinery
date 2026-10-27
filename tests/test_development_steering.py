"""Offline development-steering tests: project scope, provenance and no autopromotion."""
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.development_steering import (
    REGISTRY_SCHEMA, load_registry, project_brief, steer,
)
from cite_refinery.headless_intelligence import (
    CONFIG_SCHEMA, RECORD_SCHEMA, poll, status,
)


class DevelopmentSteeringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "private" / "inbox.sqlite"
        self.feeds = self.root / "feeds.json"
        self.registry = self.root / "projects.json"
        self.save("feeds.json", {
            "schema": CONFIG_SCHEMA,
            "feeds": [
                {"id": "external", "system": "verified-source-snapshot",
                 "kind": "record_list", "path": "external.json"},
            ],
        })
        self.save("projects.json", {
            "schema": REGISTRY_SCHEMA,
            "projects": [
                {
                    "id": "hardware", "repository": "Example/hardware",
                    "state": "active", "feeds": ["external"],
                    "watch_tags": ["robotics", "cad"],
                    "goals": ["Compare reusable robotics components"],
                    "current_priorities": ["Electromechanical validation"],
                    "benchmark": "Pinned operator-reviewed baseline",
                },
                {
                    "id": "legal", "repository": "Example/investigation",
                    "state": "paused", "feeds": ["external"],
                    "watch_tags": ["legal_research"], "goals": []
                },
            ],
        })

    def save(self, name, data):
        (self.root / name).write_text(json.dumps(data), encoding="utf-8")

    def source(self, records):
        self.save("external.json", {"schema": RECORD_SCHEMA, "records": records})

    def run_cycle(self):
        self.assertTrue(poll(self.feeds, self.db)["ok"])
        return steer(self.feeds, self.registry, self.db)

    def test_only_active_tagged_project_gets_candidate(self):
        self.source([
            {
                "id": "release:a", "title": "New kinematics library",
                "url": "https://example.org/a", "tags": ["robotics"],
                "signal": "new_capability",
            },
            {
                "id": "release:b", "title": "Unrelated crop paper",
                "url": "https://example.org/b", "tags": ["agriculture"],
                "signal": "research_finding",
            },
            {
                "id": "release:c", "title": "Legal document",
                "url": "https://example.org/c", "tags": ["legal_research"],
                "signal": "regulatory_change",
            },
        ])
        result = self.run_cycle()
        self.assertEqual(result["projects"][0]["candidates"], 1)
        self.assertEqual(result["projects"][1]["status"], "skipped_paused")
        brief = project_brief(self.db, "hardware")
        self.assertEqual(len(brief["candidates"]), 1)
        candidate = brief["candidates"][0]
        self.assertEqual(candidate["match_basis"], "structured_tag_intersection")
        self.assertEqual(candidate["status"], "candidate_review")
        self.assertIn("benchmark", candidate["next_check"].lower())
        self.assertEqual(project_brief(self.db, "legal")["candidates"], [])
        self.assertEqual(steer(self.feeds, self.registry, self.db)["projects"][0]["candidates"], 0)

    def test_explicit_target_without_topic_overlap(self):
        self.source([
            {
                "id": "direct:1", "title": "Direct project update",
                "source_url": "https://example.org/d",
                "tags": [], "signal": "project_change",
                "project_targets": ["hardware"],
            }
        ])
        self.run_cycle()
        candidate = project_brief(self.db, "hardware")["candidates"][0]
        self.assertEqual(candidate["match_basis"], "explicit_project_target")
        self.assertEqual(candidate["matched_tags"], [])

    def test_snapshot_revision_is_retriable_and_idempotent(self):
        def item(title):
            return [{
                "id": "release:1", "title": title, "url": "https://example.org/1",
                "signal": "competitor_release", "tags": ["cad"],
            }]
        self.source(item("First release"))
        self.run_cycle()
        self.source(item("Updated release"))
        self.run_cycle()
        self.assertEqual(len(project_brief(self.db, "hardware")["candidates"]), 2)
        self.assertEqual(self.run_cycle()["projects"][0]["candidates"], 0)

    def test_no_source_cursor_advance_on_missing_snapshot(self):
        self.source([
            {"id": "a", "title": "Paper", "url": "https://example.org/a",
             "signal": "research_finding", "tags": ["robotics"]}
        ])
        self.assertTrue(poll(self.feeds, self.db)["ok"])
        (self.root / "external.json").unlink()
        failed = steer(self.feeds, self.registry, self.db)
        self.assertEqual(failed["projects"][0]["status"], "source_unavailable")
        self.source([
            {"id": "a", "title": "Paper", "url": "https://example.org/a",
             "signal": "research_finding", "tags": ["robotics"]}
        ])
        result = steer(self.feeds, self.registry, self.db)
        self.assertEqual(result["projects"][0]["candidates"], 1)

    def test_intermediate_source_versions_are_not_misattributed(self):
        self.source([
            {"id": "a", "title": "Old description", "url": "https://example.org/a",
             "signal": "new_capability", "tags": ["cad"]}
        ])
        poll(self.feeds, self.db)
        self.source([
            {"id": "a", "title": "New description", "url": "https://example.org/a",
             "signal": "new_capability", "tags": ["cad"]}
        ])
        poll(self.feeds, self.db)
        out = steer(self.feeds, self.registry, self.db)["projects"][0]
        self.assertEqual(out["superseded"], 1)
        self.assertEqual(out["candidates"], 1)
        self.assertEqual(project_brief(self.db, "hardware")["candidates"][0]["title"], "New description")

    def test_broken_untrusted_leads_do_not_create_development_tasks(self):
        self.source([
            {"id": "bad:1", "title": "No source", "signal": "security_advisory",
             "tags": ["robotics"]},
            {"id": "bad:2", "title": "Malicious URL",
             "url": "http://example.org/non-tls", "signal": "security_advisory",
             "tags": ["robotics"]},
            {"id": "bad:3", "title": "Unsupported verdict",
             "url": "https://example.org/x", "signal": "proof_of_guilt",
             "tags": ["robotics"]},
            {"id": "bad:4", "title": "No explicit mapping",
             "url": "https://example.org/y", "signal": "new_capability",
             "tags": []},
        ])
        out = self.run_cycle()["projects"][0]
        self.assertEqual(out["candidates"], 0)
        self.assertEqual(out["ignored"], 4)

    def test_registry_rejects_unconfigured_feed_and_duplicate_projects(self):
        doc = json.loads(self.registry.read_text())
        doc["projects"][0]["feeds"] = ["nonexistent"]
        self.save("projects.json", doc)
        with self.assertRaises(ValueError):
            load_registry(self.registry, feed_ids={"external"})
        doc["projects"][0]["feeds"] = ["external"]
        doc["projects"][1]["id"] = "hardware"
        self.save("projects.json", doc)
        with self.assertRaises(ValueError):
            load_registry(self.registry)

    def test_inbox_only_has_audit_receipts(self):
        self.source([
            {"id": "a", "title": "Claim under review", "url": "https://example.org/a",
             "tags": ["cad"], "signal": "competitor_release"}
        ])
        self.run_cycle()
        self.assertEqual(status(self.db)["events"][0]["record_id"], "a")
        self.assertEqual(project_brief(self.db, "hardware")["authority"],
                         "lead_only_not_an_implementation_instruction")


if __name__ == "__main__":
    unittest.main()
