"""Canonical investigation entry must reuse controller and preserve safety."""
from __future__ import annotations
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
import unittest

from cite_refinery import investigation_cli, layered_cli

QUESTIONS=[
    "How can manufacturers verify battery recycling costs when purchase fees are positive?",
    "What factors complicate classroom ventilation monitoring using low-cost CO2 sensors?",
    "Why might a farmers' cooperative misreport invoice quantities after unit conversions?",
]

class CanonicalInvestigationEntryTests(unittest.TestCase):
    def run_cli(self,runner,arguments):
        output=StringIO()
        with redirect_stdout(output):
            code=runner(arguments)
        if code is not None:self.assertEqual(code,0)
        return json.loads(output.getvalue())

    def test_any_new_problem_can_start_without_domain_ontology_or_network(self):
        with TemporaryDirectory() as td:
            for question in QUESTIONS:
                initial=self.run_cli(layered_cli.main,[
                    "investigate","--workspace",td,"init",
                    "--question",question,"--max-rounds","1",
                ])
                self.assertEqual(initial["question"],question)
                self.assertEqual(initial["stage"],"plan")
                self.assertEqual(initial["authority"],"candidate_neutral_only")
                self.assertEqual(initial["module_origins"],["user_question_provisional"])
                self.assertFalse(initial["end_to_end_three_layer_validation_complete"])
                self.assertIn("independent_practical_field_observations",
                              initial["known_missing_evidence_families"])
                stored=self.run_cli(layered_cli.main,[
                    "investigate","--workspace",td,"status",
                    "--id",initial["id"],
                ])
                self.assertEqual(stored["id"],initial["id"])
                self.assertEqual(stored["stage"],"plan")
                project_root=Path(td)/"investigations"/(initial["id"]+".json")
                state=json.loads(project_root.read_text())
                self.assertEqual(state["modules"][0]["id"],"RQ-01")
                self.assertEqual(state["modules"][0]["status"],"unreviewed")
                self.assertEqual(state["modules"][0]["origin"],
                                 "user_question_provisional")
                self.assertEqual(state["rounds"],[])
                self.assertEqual(state["authority"],"candidate_neutral_only")
                self.assertNotIn("qualified",str(state["modules"]))

    def test_old_investigator_and_reviewed_modules_remain_supported(self):
        with TemporaryDirectory() as td:
            module_path=Path(td)/"modules.json"
            module_path.write_text(json.dumps([{
                "id":"SC-01","title":"Soil erosion detection",
                "summary":"Existing technical domain description"
            }]))
            q="Which types of soil erosion need monitoring before infrastructure work?"
            initial=self.run_cli(investigation_cli.main,[
                "--workspace",td,"init","--question",q,
                "--modules",str(module_path),
            ])
            self.assertEqual(initial["module_origins"],["provided_ontology"])
            stored=self.run_cli(layered_cli.main,[
                "investigate","--workspace",td,"status","--id",initial["id"]
            ])
            self.assertEqual(stored["id"],initial["id"])
            self.assertEqual(stored["authority"],"candidate_neutral_only")
            state=json.loads((Path(td)/"investigations"/(initial["id"]+".json")).read_text())
            self.assertEqual(state["modules"][0]["id"],"SC-01")

    def test_did_not_create_additional_standalone_console_script(self):
        path=Path(__file__).resolve().parents[1]/"pyproject.toml"
        with path.open("rb") as f:
            entry=tomllib.load(f)["project"]["scripts"]
        self.assertEqual(len(entry),51)
        self.assertEqual(entry["cite-refinery"],"cite_refinery.layered_cli:main")
        self.assertEqual(entry["cite-refinery-semantic-answer"],
                         "cite_refinery.source_grounded_semantic_answer:main")
        self.assertEqual(entry["cite-refinery-investigate"],"cite_refinery.investigation_cli:main")
        self.assertNotIn("cite-refinery-investigate-topic",entry)
        self.assertNotIn("cite-refinery-investigate-general",entry)

if __name__=="__main__":
    unittest.main()
