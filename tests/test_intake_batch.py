import csv
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.intake_batch import load_owner_intake_csv
from cite_refinery.intake_cli import main as intake_main
from cite_refinery.problem_commons import ProblemStatus, Visibility
from cite_refinery.problem_intake import IntakeMode


FIELDS = [
    "intake_id", "source_system", "source_ref", "title", "owner_org", "owner_statement", "geography",
    "intake_mode", "owner_confirmation", "source_observed_at", "owner_confirmation_ref", "owner_confirmed_at",
    "schedule", "affected_actors", "beneficiaries", "constraints", "available_resources", "requested_support",
    "proposed_modes", "uncertainties", "safeguarding_notes", "data_access_notes", "notes",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class IntakeBatchTests(unittest.TestCase):
    def row(self, **overrides):
        raw = {
            "title": "Synthetic community data need",
            "owner_org": "Synthetic field partner",
            "owner_statement": "A recurring reporting workflow is difficult to complete with current capacity.",
            "geography": "Taoyuan, Taiwan",
            "owner_confirmation": "not-contacted",
            "affected_actors": "staff|service users",
            "requested_support": "data analysis|workflow design",
            "uncertainties": "Need freshness not yet confirmed|baseline not supplied",
        }
        raw.update(overrides)
        return raw

    def test_batch_ids_are_deterministic_and_do_not_imply_owner_confirmation(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "needs.csv"
            write_csv(path, [self.row()])
            first = load_owner_intake_csv(path)[0]
            second = load_owner_intake_csv(path)[0]
            self.assertTrue(first.valid)
            self.assertEqual(first.intake.id, second.intake.id)
            self.assertTrue(first.intake.id.startswith("intake:batch-"))
            self.assertEqual(first.intake.intake_mode, IntakeMode.INSTITUTIONAL_BATCH)
            self.assertTrue(any("institutional batch" in warning for warning in first.warnings))
            packet = first.intake.to_problem_packet(steward="pilot-curator")
            self.assertEqual(packet.status, ProblemStatus.CANDIDATE)
            self.assertEqual(packet.visibility, Visibility.RESTRICTED)
            self.assertEqual(packet.problem_owner, "")
            self.assertEqual(packet.subproblems, [])
            self.assertFalse(packet.publishability().publishable)

    def test_pipe_separated_fields_are_preserved_as_lists(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "needs.csv"
            write_csv(path, [self.row(constraints="privacy|weekday access only")])
            record = load_owner_intake_csv(path)[0]
            self.assertEqual(record.intake.affected_actors, ["staff", "service users"])
            self.assertEqual(record.intake.constraints, ["privacy", "weekday access only"])

    def test_batch_cli_writes_candidate_review_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            csv_path = root / "needs.csv"
            out_dir = root / "out"
            write_csv(csv_path, [self.row()])
            code = intake_main([
                "batch-csv", str(csv_path),
                "--steward", "pilot-curator",
                "--rubrics", "pilot/rubrics.v0.1.json",
                "--out-dir", str(out_dir),
            ])
            self.assertEqual(code, 0)
            manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["valid_rows"], 1)
            self.assertEqual(manifest["invalid_rows"], 0)
            row = manifest["rows"][0]
            candidate = json.loads(Path(row["candidate_path"]).read_text(encoding="utf-8"))
            review = json.loads(Path(row["owner_review_path"]).read_text(encoding="utf-8"))
            self.assertEqual(candidate["status"], "candidate")
            self.assertEqual(candidate["visibility"], "restricted")
            self.assertEqual(candidate["problem_owner"], "")
            self.assertEqual(candidate["evidence"][0]["provenance"]["intake_mode"], "institutional-batch")
            self.assertEqual(review["schema"], "problem-owner-intake-review/v0.1")
            self.assertEqual(review["response"]["disposition"], "undecided")

    def test_explicit_public_listing_mode_remains_available(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "needs.csv"
            write_csv(path, [self.row(intake_mode="public-listing")])
            record = load_owner_intake_csv(path)[0]
            self.assertEqual(record.intake.intake_mode, IntakeMode.PUBLIC_LISTING)
            self.assertTrue(any("public listing" in warning for warning in record.warnings))

    def test_missing_required_columns_fail_before_partial_conversion(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.csv"
            path.write_text("title,owner_org\nA,B\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_owner_intake_csv(path)


if __name__ == "__main__":
    unittest.main()
