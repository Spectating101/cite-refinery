from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.repository_layer_cli import main
from cite_refinery.repository_layer_workspace import load_repository_layer
from cite_refinery.store import JsonStore


class RepositoryLayerCliTests(unittest.TestCase):
    def test_build_import_and_replay_preserve_unreviewed_inventory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "survey.json"
            source.write_text(json.dumps({"repositories": [
                {"full_name": "Acme/Blank", "description": ""},
                {"full_name": "Acme/Archive", "description": "Split compressed archives", "buyer_demand": "unknown"},
            ]}), encoding="utf-8")
            output = root / "result"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["build", "--survey", str(source), "--output", str(output)]), 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["repository_count"], 2)
            self.assertEqual(result["capability_count"], 0)
            self.assertEqual(result["missing_repository_count"], 0)
            reconciliation = json.loads((output / "reconciliation.json").read_text())
            self.assertEqual(reconciliation["missing_repository_ids"], [])
            self.assertEqual(reconciliation["unexpected_repository_ids"], [])
            self.assertTrue((output / "repository_layer.html").is_file())
            self.assertNotIn("buyer_demand", (output / "repository_catalog.json").read_text())
            workspace = root / "workspace"
            receipt_path = root / "receipt.json"
            argv = ["import", "--catalog", str(output / "repository_catalog.json"),
                    "--workspace", str(workspace), "--receipt", str(receipt_path)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(argv), 0)
            receipt = json.loads(receipt_path.read_text())
            project_id = receipt["project_id"]
            state = JsonStore(workspace).load()
            self.assertEqual(len(state["semantic_nodes"]), 2)
            self.assertTrue(all(n["layer"] == "program" for n in state["semantic_nodes"].values()))
            self.assertFalse(state["problem_observations"])
            saved = load_repository_layer(JsonStore(workspace), project_id)
            self.assertEqual(len(saved["repositories"]), 2)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([*argv, "--project-id", project_id]), 0)
            again = JsonStore(workspace).load()
            self.assertEqual(again["semantic_nodes"], state["semantic_nodes"])
            self.assertEqual(again["semantic_packets"], state["semantic_packets"])
            self.assertEqual(len(again["projects"]), 1)


if __name__ == "__main__":
    unittest.main()
