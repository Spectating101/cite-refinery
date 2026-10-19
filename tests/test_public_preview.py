"""The public deployment must be a reproducible public-data-only snapshot."""
import json
import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PublicPreviewTests(unittest.TestCase):
    def test_generated_atlas_contains_three_layers_and_provenance(self):
        build = runpy.run_path(str(ROOT / "scripts/build_public_preview.py"))["build"]
        with tempfile.TemporaryDirectory() as tmp:
            stats = build(Path(tmp))
            html = (Path(tmp) / "index.html").read_text(encoding="utf-8")
            data = json.loads((Path(tmp) / "snapshot.json").read_text(encoding="utf-8"))
            self.assertTrue(data["demo"])
            self.assertIn("Public demonstration", html)
            self.assertIn("No login, private project data, or live ingestion", html)
            self.assertEqual(stats["clusters"], 4)
            self.assertEqual(stats["nodes"], 12)
            self.assertEqual(stats["edges"], 12)
            project = next(iter(data["workspaces"].values()))
            self.assertEqual(project["atlas"]["layers"], ["practical", "academic", "program"])
            self.assertTrue(project["atlas"]["clusters"])
            self.assertTrue(data["coverage"])
            self.assertTrue(all("trace" in v for v in data["coverage"].values()))
            self.assertTrue(all(v["trace"]["schema"] == "cite_refinery.node_layer_trace.v1" for v in data["coverage"].values()))
            self.assertTrue(
                any(node.get("provenance_receipts") for node in project["graph_export"]["nodes"].values())
            )

if __name__ == "__main__":
    unittest.main()
