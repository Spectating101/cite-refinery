"""Tests that local Git exporter stays read-only and scoped to a vetted origin."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cite_refinery.development_steering import REGISTRY_SCHEMA, project_brief, steer
from cite_refinery.git_head_export import CHECKOUT_SCHEMA, export_heads, write_atomic
from cite_refinery.headless_intelligence import CONFIG_SCHEMA, poll


class GitHeadExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.checkout = self.root / "hardware"
        self.checkout.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "tester@example.org")
        self.git("config", "user.name", "Tester")
        self.git("remote", "add", "origin", "git@github.com:Example/hardware.git")
        (self.checkout / "README.md").write_text("first\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "Establish baseline")
        self.registry = self.root / "registry.json"
        self.checkouts = self.root / "checkouts.json"
        self.registry.write_text(json.dumps({
            "schema": REGISTRY_SCHEMA, "projects": [
                {"id": "hardware", "repository": "Example/hardware", "state": "active",
                 "feeds": ["git"], "watch_tags": ["robotics"], "goals": ["Improve tests"]}
            ]
        }), encoding="utf-8")
        self.checkouts.write_text(json.dumps({
            "schema": CHECKOUT_SCHEMA, "checkouts": [
                {"project_id": "hardware", "path": str(self.checkout)}
            ]
        }), encoding="utf-8")
        self.feeds = self.root / "feeds.json"
        self.feeds.write_text(json.dumps({
            "schema": CONFIG_SCHEMA, "feeds": [
                {"id": "git", "system": "local_git", "kind": "record_list",
                 "path": "git.json"}
            ]
        }), encoding="utf-8")
        self.snapshot = self.root / "git.json"
        self.db = self.root / "private" / "events.sqlite"

    def git(self, *arguments):
        p = subprocess.run(["git", "-C", str(self.checkout), *arguments],
                           capture_output=True, text=True, check=True)
        return p.stdout.strip()

    def test_head_change_yields_one_new_project_candidate(self):
        original = export_heads(self.registry, self.checkouts)
        self.assertEqual(len(original["records"]), 1)
        row = original["records"][0]
        self.assertEqual(row["signal"], "project_change")
        self.assertEqual(row["project_targets"], ["hardware"])
        self.assertEqual(row["commit"], self.git("rev-parse", "HEAD"))
        write_atomic(self.snapshot, original)
        self.assertTrue(poll(self.feeds, self.db)["ok"])
        self.assertEqual(steer(self.feeds, self.registry, self.db)["projects"][0]["candidates"], 1)
        # Export of the identical HEAD cannot create another event.
        write_atomic(self.snapshot, export_heads(self.registry, self.checkouts))
        self.assertEqual(poll(self.feeds, self.db)["feeds"][0]["changed"], 0)
        self.assertEqual(steer(self.feeds, self.registry, self.db)["projects"][0]["candidates"], 0)
        # An actual commit moves the input and produces a reviewable next check.
        (self.checkout / "README.md").write_text("second\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "Extend robotics implementation")
        write_atomic(self.snapshot, export_heads(self.registry, self.checkouts))
        self.assertEqual(poll(self.feeds, self.db)["feeds"][0]["changed"], 1)
        self.assertEqual(steer(self.feeds, self.registry, self.db)["projects"][0]["candidates"], 1)
        brief = project_brief(self.db, "hardware")
        self.assertEqual(len(brief["candidates"]), 2)
        self.assertEqual(brief["candidates"][0]["signal"], "project_change")

    def test_rejects_wrong_origin_without_creating_snapshot(self):
        self.git("remote", "set-url", "origin", "https://github.com/Other/repo.git")
        with self.assertRaises(ValueError):
            export_heads(self.registry, self.checkouts)
        self.assertFalse(self.snapshot.exists())

    def test_paused_project_is_not_exported(self):
        data = json.loads(self.registry.read_text(encoding="utf-8"))
        data["projects"][0]["state"] = "paused"
        self.registry.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(export_heads(self.registry, self.checkouts)["records"], [])


if __name__ == "__main__":
    unittest.main()
