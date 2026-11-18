"""Native persistence and routing checks without creating a network listener."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import quote

from cite_refinery.repository_layer import build_repository_layer
from cite_refinery.repository_layer_workspace import load_repository_layer, save_repository_layer
from cite_refinery.store import JsonStore
from cite_refinery.web_shell import _handler


class RepositoryLayerWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = JsonStore(self.root / "workspace")
        self.project_id = "repository-project:inventory/primary"
        self.other_project = "repository-project:other"
        state = self.store.load()
        state["projects"] = {
            self.project_id: {"id": self.project_id, "title": '<img src=x onerror="evil()"> Inventory'},
            self.other_project: {"id": self.other_project, "title": "Another inventory"},
        }
        self.store.save(state)
        self.catalog = self.build_catalog("Archive utility")

    def build_catalog(self, description):
        snapshot = self.root / "snapshot.json"
        snapshot.write_text(json.dumps({
            "schema": "cite_refinery.opportunity_atlas_github_snapshot.v1",
            "observed_at": "2026-11-18T00:00:00Z",
            "repositories": [{"full_name": "Acme/Archive", "description": description,
                              "language": "Python", "found_in": ["archives"]}],
        }), encoding="utf-8")
        return build_repository_layer([snapshot])

    def receipt(self):
        return self.store.load()["repository_layers"][self.project_id]

    def change_receipt(self, **changes):
        state = self.store.load()
        state["repository_layers"][self.project_id].update(changes)
        self.store.save(state)

    def request(self, path):
        # Exercise the real handler's routing, serialization and error boundary;
        # no socket or fake alternative router is required.
        handler_type = _handler(str(self.store.workspace))
        handler = handler_type.__new__(handler_type)
        handler.path = path
        handler.wfile = BytesIO()
        response = {"headers": {}}
        handler.send_response = lambda status: response.update(status=int(status))
        handler.send_header = lambda name, value: response["headers"].update({name: value})
        handler.end_headers = lambda: None
        handler.do_GET()
        response["body"] = handler.wfile.getvalue()
        self.assertEqual(int(response["headers"]["Content-Length"]), len(response["body"]))
        self.assertEqual(response["headers"]["Cache-Control"], "no-store")
        return response

    def test_saves_content_addressed_snapshots_without_bootstrapping_problem(self):
        before = self.store.load()
        receipt = save_repository_layer(self.store, self.project_id, self.catalog)
        path = self.store.workspace / receipt["relative_path"]
        self.assertEqual(path.parent.name, hashlib.sha256(self.project_id.encode()).hexdigest())
        self.assertEqual(path.name, self.catalog["catalog_digest"] + ".json")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), receipt["sha256"])
        self.assertEqual(load_repository_layer(self.store, self.project_id), self.catalog)
        self.assertEqual(save_repository_layer(self.store, self.project_id, self.catalog), receipt)
        after = self.store.load()
        after.pop("repository_layers")
        self.assertEqual(after, before)

        next_catalog = self.build_catalog("Archive utility with a revised description")
        next_receipt = save_repository_layer(self.store, self.project_id, next_catalog)
        self.assertNotEqual(receipt["relative_path"], next_receipt["relative_path"])
        self.assertTrue(path.exists(), "Earlier immutable snapshot must remain available")
        self.assertEqual(json.loads(path.read_bytes()), self.catalog)
        self.assertEqual(load_repository_layer(self.store, self.project_id), next_catalog)

    def test_rejects_traversal_absolute_paths_and_other_project_receipts(self):
        original = save_repository_layer(self.store, self.project_id, self.catalog)
        other = save_repository_layer(self.store, self.other_project, self.catalog)
        for invalid in ("../state.json", str(self.store.path.resolve()), "repository_layers/../state.json", other["relative_path"]):
            with self.subTest(path=invalid):
                self.change_receipt(relative_path=invalid)
                with self.assertRaises(ValueError):
                    load_repository_layer(self.store, self.project_id)
        self.change_receipt(**original)
        self.assertEqual(load_repository_layer(self.store, self.other_project), self.catalog)
        self.assertEqual(load_repository_layer(self.store, self.project_id), self.catalog)

    def test_rejects_symbolic_link_even_when_target_bytes_are_valid(self):
        receipt = save_repository_layer(self.store, self.project_id, self.catalog)
        path = self.store.workspace / receipt["relative_path"]
        outside = self.root / "elsewhere.json"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            load_repository_layer(self.store, self.project_id)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            save_repository_layer(self.store, self.project_id, self.catalog)
        self.assertEqual(json.loads(outside.read_bytes()), self.catalog)

    def test_file_hash_catalogue_digest_and_coverage_each_bind_the_saved_snapshot(self):
        receipt = save_repository_layer(self.store, self.project_id, self.catalog)
        path = self.store.workspace / receipt["relative_path"]
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            load_repository_layer(self.store, self.project_id)
        with self.assertRaisesRegex(ValueError, "immutable"):
            save_repository_layer(self.store, self.project_id, self.catalog)
        self.assertEqual(path.read_bytes(), original + b" ", "Save must not repair an immutable artifact silently")

        changed = deepcopy(self.catalog)
        changed["repositories"][0]["description"] = "Unrecorded alteration"
        body = json.dumps(changed).encode()
        path.write_bytes(body)
        self.change_receipt(sha256=hashlib.sha256(body).hexdigest())
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            load_repository_layer(self.store, self.project_id)

        path.write_bytes(original)
        self.change_receipt(**receipt)
        self.change_receipt(coverage={**receipt["coverage"], "repository_count": 999})
        with self.assertRaisesRegex(ValueError, "coverage"):
            load_repository_layer(self.store, self.project_id)

    def test_project_existence_and_catalogue_validation_are_required(self):
        with self.assertRaises(KeyError):
            save_repository_layer(self.store, "unknown", self.catalog)
        with self.assertRaises(KeyError):
            load_repository_layer(self.store, self.project_id)
        with self.assertRaises(ValueError):
            save_repository_layer(self.store, self.project_id, {**self.catalog, "scope": "combined"})
        self.assertFalse((self.store.workspace / "repository_layers").exists())
        save_repository_layer(self.store, self.project_id, self.catalog)
        state = self.store.load()
        del state["projects"][self.project_id]
        self.store.save(state)
        with self.assertRaises(KeyError):
            load_repository_layer(self.store, self.project_id)

    def test_native_routes_expose_only_the_saved_repository_layer(self):
        save_repository_layer(self.store, self.project_id, self.catalog)
        before = self.store.load()
        project_path = quote(self.project_id, safe="")
        index = self.request("/repositories")
        self.assertEqual(index["status"], 200)
        index_html = index["body"].decode()
        self.assertIn("/repositories/" + project_path, index_html)
        self.assertIn("&lt;img", index_html)
        self.assertNotIn("<img", index_html)
        self.assertIn("1 repositories", index_html)
        self.assertNotIn("Another inventory", index_html)

        page = self.request("/repositories/" + project_path)
        self.assertEqual(page["status"], 200)
        self.assertIn("text/html", page["headers"]["Content-Type"])
        page_html = page["body"].decode()
        self.assertIn('id="repo-layer-data"', page_html)
        self.assertIn(self.catalog["catalog_digest"], page_html)
        self.assertNotIn("Three-layer semantic workspace", page_html)
        self.assertNotIn("layer_presence", page_html)

        api = self.request("/api/projects/" + project_path + "/repository-layer")
        self.assertEqual(api["status"], 200)
        self.assertEqual(json.loads(api["body"]), self.catalog)
        missing = self.request("/api/projects/" + quote(self.other_project, safe="") + "/repository-layer")
        self.assertEqual(missing["status"], 404)
        self.assertEqual(self.request("/repositories/unknown")["status"], 404)
        shell = self.request("/")["body"].decode()
        self.assertIn('href="/repositories">Repositories</a>', shell)
        self.assertIn("Three-layer semantic workspace", shell)
        self.assertEqual(self.store.load(), before, "Browsing must not add problem records or mutate state")

    def test_empty_index_and_corrupt_layer_errors_remain_explicit(self):
        response = self.request("/repositories/")
        self.assertEqual(response["status"], 200)
        self.assertIn(b"No repository layers have been saved", response["body"])
        receipt = save_repository_layer(self.store, self.project_id, self.catalog)
        (self.store.workspace / receipt["relative_path"]).write_text("{}", encoding="utf-8")
        project_path = quote(self.project_id, safe="")
        for route in ("/repositories/" + project_path, "/api/projects/" + project_path + "/repository-layer"):
            with self.subTest(route=route):
                response = self.request(route)
                self.assertEqual(response["status"], 400)
                self.assertIn("SHA-256 mismatch", json.loads(response["body"])["error"])
        self.assertIn(b"could not be verified", self.request("/repositories")["body"])


if __name__ == "__main__":
    unittest.main()
