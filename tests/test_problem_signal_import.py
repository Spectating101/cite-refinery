import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.problem_cli import main
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus


class ProblemSignalImportTests(unittest.TestCase):
    def write_signals(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "schema": "problem-signals/v0.1",
                    "signals": [
                        {
                            "id": "signal:1",
                            "source_system": "ExampleSource",
                            "source_ref": "https://example.test/signal/1",
                            "title": "Investigate an observed access failure",
                            "observed_condition": "A public source reports repeated access failures.",
                            "domain": "public-good",
                            "geography": "example",
                            "visibility": "public",
                            "metadata": {
                                "signal_type": "open_data_candidate",
                                "do_not_publish": True,
                                "hypothesis": "The mechanism remains unknown."
                            }
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_signal_import_creates_nonpublic_candidate_with_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            signal_path = root / "signals.json"
            state_path = root / "state.json"
            self.write_signals(signal_path)
            self.assertEqual(main(["--state", str(state_path), "signal-import", str(signal_path), "--steward", "curator"]), 0)
            commons = ProblemCommons.load(state_path)

        self.assertEqual(len(commons.problems), 1)
        packet = next(iter(commons.problems.values()))
        self.assertEqual(packet.status, ProblemStatus.CANDIDATE)
        self.assertEqual(commons.list_public(), [])
        self.assertIn("do-not-publish-before-curation", packet.tags)
        self.assertEqual(packet.external_refs[0].system, "ExampleSource")
        self.assertIn("signal:1", packet.external_refs[0].notes)

    def test_reimport_same_source_ref_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            signal_path = root / "signals.json"
            state_path = root / "state.json"
            self.write_signals(signal_path)
            main(["--state", str(state_path), "signal-import", str(signal_path), "--steward", "curator"])
            main(["--state", str(state_path), "signal-import", str(signal_path), "--steward", "curator"])
            commons = ProblemCommons.load(state_path)
        self.assertEqual(len(commons.problems), 1)

    def test_signal_import_rejects_unknown_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            signal_path = root / "signals.json"
            signal_path.write_text('{"schema":"wrong","signals":[]}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                main(["--state", str(root / "state.json"), "signal-import", str(signal_path), "--steward", "curator"])


if __name__ == "__main__":
    unittest.main()
