import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_contribution_rehearsal import run_rehearsal


class ContributionRehearsalTests(unittest.TestCase):
    def test_realistic_revise_then_accept_rehearsal_emits_inspectable_pack(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "rehearsal"
            manifest = run_rehearsal(out)

            self.assertEqual(manifest["result"], "pass")
            self.assertEqual(manifest["workflow"], ["SUBMIT", "REVISE", "REVISION_R1", "RESUBMIT", "ACCEPT"])
            self.assertEqual(manifest["problem_status"], "open")
            self.assertEqual(manifest["attempt_status"], "accepted")
            self.assertEqual(manifest["attempt_count"], 1)
            self.assertEqual(manifest["review_verdicts"], ["revise", "accept"])
            self.assertEqual(manifest["outcome_count"], 0)
            self.assertEqual(manifest["authority_decision_count"], 0)
            self.assertTrue(manifest["no_op_revision_rejected"])
            self.assertEqual(manifest["private_locator_leak_check"], "pass")

            expected = {
                "manifest.json",
                "transcript.json",
                "friction.json",
                "problem-commons.json",
                "workspace-v0.json",
                "submission-v0.json",
                "review-v0.json",
                "projection-v0.json",
                "workspace-r1.json",
                "submission-r1.json",
                "review-r1.json",
                "projection-r1.json",
                "README.md",
            }
            self.assertTrue(expected.issubset({path.name for path in out.iterdir()}))

            transcript = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
            no_op = next(item for item in transcript if item["label"] == "prove no-op revision rejection")
            self.assertEqual(no_op["exit_code"], 2)
            self.assertIn("must change contributor work", no_op["stdout"])

            friction = json.loads((out / "friction.json").read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in friction], ["F1", "F2", "F3", "F4"])

            final_state = json.loads((out / "problem-commons.json").read_text(encoding="utf-8"))
            serialized = json.dumps(final_state)
            self.assertNotIn("initial_analysis.md", serialized)
            self.assertNotIn("revised_analysis.md", serialized)
            self.assertNotIn("intake_records.csv", serialized)

    def test_rehearsal_refuses_to_overwrite_nonempty_evidence_directory(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "rehearsal"
            out.mkdir()
            (out / "existing.txt").write_text("preserve\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not empty"):
                run_rehearsal(out)
            self.assertEqual((out / "existing.txt").read_text(encoding="utf-8"), "preserve\n")


if __name__ == "__main__":
    unittest.main()
