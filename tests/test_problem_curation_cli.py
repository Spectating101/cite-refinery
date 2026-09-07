import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.problem_cli import main
from cite_refinery.problem_commons import ProblemCommons, ProblemStatus


class ProblemCurationCliTests(unittest.TestCase):
    def test_candidate_can_be_curated_to_open_without_editing_state_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state.json"
            signals = root / "signals.json"
            signals.write_text(json.dumps({
                "schema": "problem-signals/v0.1",
                "signals": [{
                    "id": "signal:curate",
                    "source_system": "Example",
                    "source_ref": "https://example.test/curate",
                    "title": "Investigate repeated access failure",
                    "observed_condition": "A reviewed source reports repeated access failure.",
                    "domain": "public-good",
                    "visibility": "public",
                    "metadata": {"do_not_publish": True}
                }]
            }), encoding="utf-8")

            main(["--state", str(state), "signal-import", str(signals), "--steward", "curator"])
            commons = ProblemCommons.load(state)
            problem_id = next(iter(commons.problems))

            def run(*args: str) -> None:
                self.assertEqual(main(["--state", str(state), *args]), 0)

            run("packet-set", problem_id, "unresolved_core", "Determine which mechanism causes the repeated access failure.")
            run("packet-set", problem_id, "authority_boundary", "Any real-world change requires the service owner's approval.")
            run("packet-set", problem_id, "problem_owner", "example-service-owner")
            run("context-add", problem_id, "affected_actor", "service users")
            run("context-add", problem_id, "constraint", "privacy")
            run("context-add", problem_id, "knowledge_frontier", "Mechanism is not yet established.")
            run("context-add", problem_id, "implementation_step", "Run a non-consequential shadow test first.")
            run("evidence-add", problem_id, "--source", "reviewed source", "--locator", "https://example.test/evidence", "--summary", "Repeated access failures are documented.", "--confidence", "reviewed", "--visibility", "public")
            run("success-add", problem_id, "--metric", "verified failure rate", "--target", "lower than frozen baseline", "--measurement", "pre/post service log", "--falsification", "no reduction or new harm", "--guardrail", "no automated denial")
            run("capability-add", problem_id, "service funnel analysis", "--state", "available", "--description", "Transition-level analysis")
            run("data-add", problem_id, "service transition log", "--access", "operator-approved", "--visibility", "restricted", "--sensitivity", "administrative")
            run("subproblem-add", problem_id, "Establish mechanism", "--description", "Distinguish competing causes.", "--kind", "research", "--skill", "statistics", "--output", "mechanism comparison")
            run("steward-review", problem_id, "--reviewer", "domain-reviewer", "--verdict", "accept", "--check", "condition=true", "--check", "authority=true")
            run("transition", problem_id, "researching", "--actor", "curator", "--reason", "begin review")
            run("transition", problem_id, "verified", "--actor", "reviewer", "--reason", "minimum evidence and scope verified")
            run("transition", problem_id, "open", "--actor", "reviewer", "--reason", "decomposition ready for external attempts")

            loaded = ProblemCommons.load(state)
            packet = loaded.get(problem_id)
            self.assertEqual(packet.status, ProblemStatus.OPEN)
            self.assertEqual(len(packet.evidence), 1)
            self.assertEqual(len(packet.success_criteria), 1)
            self.assertEqual(len(packet.capability_needs), 1)
            self.assertEqual(len(packet.data_resources), 1)
            self.assertEqual(len(packet.steward_reviews), 1)
            self.assertEqual(loaded.list_public()[0].id, problem_id)

    def test_duplicate_check_is_available_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            main(["--state", str(state), "init", "Repeated service access failure", "--condition", "Users repeatedly fail to access a service.", "--unresolved", "Identify the access mechanism.", "--steward", "c"])
            main(["--state", str(state), "init", "Service access failures repeat", "--condition", "Users repeatedly fail to access the same service.", "--unresolved", "Identify the access mechanism.", "--steward", "c"])
            commons = ProblemCommons.load(state)
            ids = list(commons.problems)
            matches = commons.duplicate_candidates(commons.get(ids[1]), threshold=0.2)
            self.assertTrue(any(problem_id == ids[0] for problem_id, _ in matches))


if __name__ == "__main__":
    unittest.main()
