import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class DraftAdmissionCLITests(unittest.TestCase):
    def test_taoyuan_draft_import_and_assessment_stay_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commons = root / "commons.json"
            stages = root / "stages.json"
            governance = root / "governance.json"
            pilot = root / "pilot.json"
            operations = root / "operations.json"
            base = [
                sys.executable, "-m", "cite_refinery.operations_cli",
                "--commons", str(commons),
                "--stages", str(stages),
                "--governance", str(governance),
                "--pilot", str(pilot),
                "--operations", str(operations),
                "--policy", "pilot/operations-policy.v0.1.json",
            ]
            imported = subprocess.run(
                base + [
                    "draft-import", "pilot/drafts/taoyuan-mobility.candidate.v0.1.json",
                    "--actor", "cli-curator",
                ],
                check=True, capture_output=True, text=True,
            )
            import_payload = json.loads(imported.stdout)
            self.assertEqual(import_payload["problem_id"], "problem:taoyuan-mobility-candidate-001")
            self.assertEqual(import_payload["status"], "researching")
            self.assertEqual(import_payload["visibility"], "restricted")

            assessed = subprocess.run(
                base + ["assess", "problem:taoyuan-mobility-candidate-001"],
                check=True, capture_output=True, text=True,
            )
            assessment = json.loads(assessed.stdout)
            self.assertEqual(assessment["phase"], "curation")
            self.assertFalse(assessment["eligible_for_verification"])
            self.assertTrue(any("production" in item for item in assessment["blockers"]))
            self.assertTrue(any("reviewed_evidence" in item for item in assessment["blockers"]))

            state = json.loads(commons.read_text(encoding="utf-8"))
            problem = state["problems"][0]
            self.assertEqual(problem["status"], "researching")
            self.assertEqual(problem["visibility"], "restricted")
            self.assertEqual(problem["attempts"], [])
            self.assertEqual(problem["authority_decisions"], [])
            self.assertEqual(problem["outcomes"], [])

            ledger = json.loads(operations.read_text(encoding="utf-8"))
            self.assertEqual(ledger["schema"], "problem-operations/v0.1")
            self.assertEqual(len(ledger["receipts"]), 1)
            self.assertEqual(ledger["receipts"][0]["action"], "draft-import")

    def test_cli_rejects_tampered_public_taoyuan_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = json.loads(Path("pilot/drafts/taoyuan-mobility.candidate.v0.1.json").read_text(encoding="utf-8"))
            source["visibility"] = "public"
            tampered = root / "tampered.json"
            tampered.write_text(json.dumps(source), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, "-m", "cite_refinery.operations_cli",
                    "--commons", str(root / "commons.json"),
                    "--stages", str(root / "stages.json"),
                    "--governance", str(root / "governance.json"),
                    "--pilot", str(root / "pilot.json"),
                    "--operations", str(root / "operations.json"),
                    "--policy", "pilot/operations-policy.v0.1.json",
                    "draft-import", str(tampered), "--actor", "cli-curator",
                ],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("rejects public packet visibility", result.stderr)


if __name__ == "__main__":
    unittest.main()
