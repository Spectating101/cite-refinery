"""Offline GitHub release source adapter tests using pinned response fixtures."""
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.development_steering import REGISTRY_SCHEMA, project_brief, steer
from cite_refinery.github_release_export import SCHEMA, collect_releases, load_sources, write_atomic
from cite_refinery.headless_intelligence import CONFIG_SCHEMA, poll


class GithubReleaseExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = self.root / "projects.json"
        self.sources = self.root / "upstream.json"
        self.feeds = self.root / "feeds.json"
        self.snapshot = self.root / "releases.json"
        self.db = self.root / "private" / "events.sqlite"
        self.write(self.registry, {
            "schema": REGISTRY_SCHEMA,
            "projects": [{"id": "refinery", "repository": "Example/refinery",
                          "state": "active", "feeds": ["releases"],
                          "watch_tags": ["knowledge_graph"], "goals": []}],
        })
        self.write(self.sources, {
            "schema": SCHEMA,
            "repositories": [{
                "repository": "getzep/graphiti",
                "signal": "competitor_release",
                "tags": ["knowledge_graph"],
                "project_targets": ["refinery"],
                "published_since": "2026-10-01T00:00:00Z",
            }],
        })
        self.write(self.feeds, {
            "schema": CONFIG_SCHEMA,
            "feeds": [{
                "id": "releases", "system": "github_public_release",
                "kind": "record_list", "path": "releases.json"
            }],
        })

    @staticmethod
    def write(path, payload):
        path.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def response(name="Graph update", published="2026-10-10T12:00:00Z"):
        return [
            {
                "id": 100, "tag_name": "v2.0.0", "name": name, "published_at": published,
                "draft": False, "prerelease": False,
            },
            {
                "id": 101, "tag_name": "v2.1.0-rc1", "name": "Unstable",
                "published_at": "2026-10-12T12:00:00Z",
                "draft": False, "prerelease": True,
            },
            {
                "id": 102, "tag_name": "internal", "name": "Draft",
                "published_at": "2026-10-12T12:00:00Z",
                "draft": True, "prerelease": False,
            },
        ]

    def test_pinned_public_release_routes_one_project_just_once(self):
        def fake(url, _token):
            self.assertEqual(url,
                             "https://api.github.com/repos/getzep/graphiti/releases?per_page=10")
            return self.response()
        snapshot = collect_releases(self.sources, self.registry, fetcher=fake)
        self.assertEqual(len(snapshot["records"]), 1)
        record = snapshot["records"][0]
        self.assertEqual(record["id"], "github-release:getzep/graphiti:100")
        self.assertEqual(record["source_url"],
                         "https://github.com/getzep/graphiti/releases/tag/v2.0.0")
        self.assertNotIn("body", record)
        write_atomic(self.snapshot, snapshot)
        self.assertTrue(poll(self.feeds, self.db)["ok"])
        self.assertEqual(steer(self.feeds, self.registry, self.db)["projects"][0]["candidates"], 1)
        self.assertEqual(project_brief(self.db, "refinery")["candidates"][0]["signal"],
                         "competitor_release")
        self.assertEqual(steer(self.feeds, self.registry, self.db)["projects"][0]["candidates"], 0)

    def test_bad_upstream_response_fails_before_replacing_checkpoint(self):
        self.write(self.snapshot, {"schema": "prior-snapshot", "records": []})
        def bad_response(_url, _token):
            return {"message": "rate limit"}
        with self.assertRaises(ValueError):
            collect_releases(self.sources, self.registry, fetcher=bad_response)
        self.assertEqual(json.loads(self.snapshot.read_text())["schema"], "prior-snapshot")

    def test_filters_older_releases_and_rejects_unknown_projects(self):
        rows = collect_releases(self.sources, self.registry,
                                fetcher=lambda _url, _token:
                                    self.response(published="2026-09-30T12:00:00Z"))
        self.assertEqual(rows["records"], [])
        source = json.loads(self.sources.read_text())
        source["repositories"][0]["project_targets"] = ["not_registered"]
        self.write(self.sources, source)
        with self.assertRaises(ValueError):
            load_sources(self.sources, project_ids={"refinery"})

    def test_prerelease_requires_explicit_consent(self):
        source = json.loads(self.sources.read_text())
        source["repositories"][0]["include_prereleases"] = True
        self.write(self.sources, source)
        result = collect_releases(self.sources, self.registry,
                                  fetcher=lambda _url, _token: self.response())
        self.assertEqual(len(result["records"]), 2)


if __name__ == "__main__":
    unittest.main()
