import json
import os
import stat
import tempfile
import unittest

from cite_refinery.cite import CiteAgentCLIAdapter
from cite_refinery.orchestrator import CiteRefinery


def fake_command(tmp: str, payload: dict | None, exit_code: int, stdout_text: str | None = None) -> str:
    path = os.path.join(tmp, "fake-cite-agent-research")
    body = stdout_text if stdout_text is not None else json.dumps(payload)
    with open(path, "w") as fh:
        fh.write(f"#!/bin/sh\ncat <<'JSON'\n{body}\nJSON\necho 'log line' >&2\nexit {exit_code}\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


GROUNDED = {
    "schema_version": 1, "tool": "ground", "status": "completed",
    "claims": [
        {"claim": "A", "verdict": "supported", "evidence": [{"title": "t", "quote": "q"}]},
        {"claim": "B", "verdict": "not_found", "evidence": []},
    ],
}


class CiteAdapterTests(unittest.TestCase):
    def test_completed_json_is_structured_and_summarised(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = CiteAgentCLIAdapter(command=fake_command(tmp, GROUNDED, 0)).ground("- A\n- B")
            self.assertEqual(audit.status, "completed")
            self.assertEqual(audit.structured["claims"][0]["verdict"], "supported")
            self.assertIn("1 supported", audit.raw)
            self.assertIn("1 not_found", audit.raw)

    def test_not_run_and_non_json_are_never_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            not_run = {"schema_version": 1, "tool": "ground", "status": "not_run", "claims": [], "error": "no model"}
            self.assertEqual(CiteAgentCLIAdapter(command=fake_command(tmp, not_run, 3)).ground("x").status, "not_run")
            garbage = CiteAgentCLIAdapter(command=fake_command(tmp, None, 0, stdout_text="Error: no papers")).ground("x")
            self.assertEqual(garbage.status, "error")
            lying = CiteAgentCLIAdapter(command=fake_command(tmp, GROUNDED, 2)).ground("x")
            self.assertEqual(lying.status, "error")

    def test_orchestrator_records_each_claims_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            payload = {**GROUNDED, "claims": [
                {"claim": "Claim A is about something measurable.", "verdict": "supported", "evidence": [{"quote": "q"}]},
                {"claim": "Claim B is about something else entirely.", "verdict": "not_found", "evidence": []},
            ]}
            app.cite = CiteAgentCLIAdapter(command=fake_command(tmp, payload, 0))
            project = app.init_project("Verdicts", "Record per-claim grounding")
            a = app.add_claim(project.id, "Claim A is about something measurable.")
            b = app.add_claim(project.id, "Claim B is about something else entirely.")
            app.ground(project.id)
            claims = app.store.load()["claims"]
            self.assertEqual(claims[a.id]["status"], "audited")
            self.assertEqual(claims[a.id]["grounding"]["verdict"], "supported")
            self.assertEqual(claims[b.id]["grounding"]["verdict"], "not_found")
            self.assertEqual(claims[a.id]["grounding"]["evidence_count"], 1)


if __name__ == "__main__":
    unittest.main()
