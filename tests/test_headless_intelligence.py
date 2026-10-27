"""End-to-end offline regression for the headless, provenance-first inbox."""
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.headless_intelligence import (
    CONFIG_SCHEMA, RECORD_SCHEMA, load_config, poll, status,
)


class HeadlessIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "state" / "headless.sqlite"
        self.config = self.root / "feeds.json"

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value), encoding="utf-8")

    def set_feeds(self, feeds):
        self.write("feeds.json", {"schema": CONFIG_SCHEMA, "feeds": feeds})

    def test_record_list_is_idempotent_and_tracks_revisions(self):
        self.set_feeds([{
            "id": "trend", "system": "trendradar", "kind": "record_list",
            "path": "trend.json",
        }])
        self.write("trend.json", {"schema": RECORD_SCHEMA, "records": [
            {"id": "notice-1", "title": "Initial lead", "source_url": "https://example.org/1"}
        ]})
        first = poll(self.config, self.db)
        self.assertTrue(first["ok"])
        self.assertEqual(first["feeds"][0]["created"], 1)
        again = poll(self.config, self.db)
        self.assertEqual(again["feeds"][0]["created"], 0)
        self.assertEqual(again["feeds"][0]["changed"], 0)
        self.write("trend.json", {"schema": RECORD_SCHEMA, "records": [
            {"id": "notice-1", "title": "Changed source lead", "source_url": "https://example.org/1"},
            {"id": "notice-2", "title": "Second lead"}
        ]})
        third = poll(self.config, self.db)
        self.assertEqual((third["feeds"][0]["created"], third["feeds"][0]["changed"]), (1, 1))
        state = status(self.db)
        self.assertEqual([e["change"] for e in state["events"]], ["created", "changed", "created"])
        self.assertEqual(state["feeds"][0]["record_count"], 2)
        self.assertEqual(state["feeds"][0]["insight"]["authority"], "lead_only")

    def test_malformed_or_missing_snapshot_fails_closed(self):
        self.set_feeds([{"id": "cite", "system": "cite-agent", "kind": "record_list",
                         "path": "research.json"}])
        failed = poll(self.config, self.db)
        self.assertFalse(failed["ok"])
        self.assertEqual(status(self.db)["events"], [])
        self.write("research.json", {"schema": RECORD_SCHEMA, "records": [
            {"id": "paper:1", "title": "Research discovery"}
        ]})
        self.assertTrue(poll(self.config, self.db)["ok"])
        self.write("research.json", {"schema": RECORD_SCHEMA, "records": [
            {"id": "paper:1"}, {"id": "paper:1"}
        ]})
        self.assertFalse(poll(self.config, self.db)["ok"])
        self.assertEqual(len(status(self.db)["events"]), 1)
        self.assertEqual(status(self.db)["feeds"][0]["record_count"], 1)

    def test_semantic_packet_preserves_candidate_authority(self):
        self.set_feeds([{
            "id": "three-layer", "system": "cite-refinery",
            "kind": "semantic_packet", "path": "reviewed-packet.json"
        }])
        self.write("reviewed-packet.json", {
            "schema": "cite_refinery.semantic_graph.v1",
            "project_id": "project-1",
            "source_system": "three-layer-candidate-only",
            "nodes": [
                {"key": "problem", "layer": "practical", "kind": "problem_claim",
                 "statement": "Observed gap", "source_refs": ["https://example.org/problem"]},
                {"key": "program", "layer": "program", "kind": "capability",
                 "statement": "Possible software component", "source_refs": ["https://example.org/program"]},
            ],
            "edges": [{"source": "program", "target": "problem", "relation": "ADDRESSES",
                       "status": "candidate", "evidence_refs": ["https://example.org/fit"]}],
        })
        response = poll(self.config, self.db)
        self.assertTrue(response["ok"])
        self.assertEqual(response["feeds"][0]["insight"]["problems"], 1)
        self.assertEqual(response["feeds"][0]["insight"]["findings"], 1)
        self.assertEqual(response["feeds"][0]["insight"]["authority"],
                         "source_bounded_candidate_interpretation_only")
        self.assertEqual(len(status(self.db)["events"]), 3)
        self.assertEqual(poll(self.config, self.db)["feeds"][0]["changed"], 0)

    def test_empty_snapshot_is_not_a_deletion_instruction(self):
        self.set_feeds([{"id": "source", "system": "research_scout",
                         "kind": "record_list", "path": "scout.json"}])
        self.write("scout.json", {"schema": RECORD_SCHEMA, "records": [{"id": "x"}]})
        poll(self.config, self.db)
        self.write("scout.json", {"schema": RECORD_SCHEMA, "records": []})
        result = poll(self.config, self.db)
        self.assertEqual(result["feeds"][0]["items"], 0)
        self.assertEqual(len(status(self.db)["events"]), 1)

    def test_configuration_validation(self):
        self.set_feeds([
            {"id": "same", "system": "one", "kind": "record_list", "path": "one.json"},
            {"id": "same", "system": "two", "kind": "record_list", "path": "two.json"},
        ])
        with self.assertRaises(ValueError):
            load_config(self.config)


if __name__ == "__main__":
    unittest.main()
