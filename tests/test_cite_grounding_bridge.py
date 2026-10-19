"""No automatic upgrade from a claimed Cite grounding verdict to true support."""
import copy
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cite_refinery.hosted_store import WorkspaceDB, _MemoryStore
from cite_refinery.cite_literature_bridge import convert_search, resolve_target
from cite_refinery.cite_grounding_bridge import convert_grounding
from cite_refinery.cite_grounding_cli import main
from cite_refinery.workspace import ProductWorkspace


def case_packet():
    return {
        "schema": "cite_refinery.semantic_graph.v1", "source_system": "nocturnal",
        "clusters": [{"key": "nocturnal-china-kangmei-2020", "title": "Kangmei source case",
                      "provenance": {"candidate_id": "china-kangmei-2020",
                                     "frozen_empirical_commit": "a"*40}}],
        "nodes": [
            {"key": "nocturnal-china-kangmei-2020-scope",
             "statement": "Kangmei empirical case scope", "layer": "neutral",
             "clusters": ["nocturnal-china-kangmei-2020"]},
            {"key": "event", "statement": "Official court ruling",
             "layer": "practical", "kind": "observation",
             "clusters": ["nocturnal-china-kangmei-2020"],
             "source_refs": ["https://example.org/court"]},
        ],
        "edges": [{"source": "event", "target": "nocturnal-china-kangmei-2020-scope",
                   "relation": "CONTEXT_FOR", "status": "qualified"}],
    }


ABSTRACT = ("The empirical study based on Kangmei reports that a negative market reaction "
            "occurred among firms audited by accounting firms facing litigation.")


def bibliography():
    return {
        "tool": "search", "status": "completed", "paper_count": 1,
        "topic": "Kangmei market reaction",
        "papers": [{"source": "semantic_scholar", "title": "Kangmei litigation and auditor response",
                    "abstract": ABSTRACT, "doi": "10.1234/kangmei.test",
                    "authors": ["Researcher"], "year": 2023, "venue": "Synthetic Journal"}],
    }


def grounding():
    return {
        "tool": "ground", "status": "completed", "schema_version": 1,
        "claims": [{
            "claim": "An empirical study reports negative market reaction among the affected auditing firms' clients.",
            "verdict": "supported", "rejected_quotes": 0,
            "evidence": [{"doi": "10.1234/kangmei.test",
                          "title": "Kangmei litigation and auditor response",
                          "quote": "a negative market reaction occurred among firms audited by accounting firms facing litigation"}],
            "reason": "Quote-backed but not full-text examined",
        }],
    }


class AcademicGroundingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "private.sqlite3")
        self.db = WorkspaceDB(self.path)
        self.tenant = self.db.create_tenant("Research", "owner")
        self.owner = self.tenant["owner_user_id"]
        self.project = self.db.create_project(self.owner, self.tenant["tenant_id"], "Kangmei", "Case")
        for packet in (case_packet(),):
            self._ingest(packet)
        target = resolve_target(self.db.project_state(self.owner, self.project),
                                self.project, "china-kangmei-2020")
        self._ingest(convert_search(bibliography(), target))

    def tearDown(self):
        self.tmp.cleanup()

    def _ingest(self, packet):
        r = self.db.preview(self.owner, self.project, packet)
        self.db.enqueue(self.owner, self.project, packet,
                        r["project_revision"], r["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")

    def _convert(self, receipt=None):
        return convert_grounding(
            receipt or grounding(), self.db.project_state(self.owner, self.project),
            self.project, "china-kangmei-2020")

    def test_abstr_quote_creates_qualified_paper_relation_but_candidate_case(self):
        packet = self._convert()
        self.assertEqual(len(packet["nodes"]), 1)
        self.assertEqual(packet["nodes"][0]["kind"], "academic_claim")
        self.assertEqual(packet["nodes"][0]["layer"], "academic")
        self.assertFalse(packet["nodes"][0]["provenance"]["independent_fulltext_verification"])
        self.assertEqual({e["relation"]: e["status"] for e in packet["edges"]},
                         {"DERIVED_FROM": "qualified", "RELATED_TO": "candidate"})
        self.assertEqual(packet["conversion_metadata"]["asserted_practical_academic_links"], 0)
        before = self.db.project_state(self.owner, self.project)
        review = self.db.preview(self.owner, self.project, packet)
        self.assertEqual(review["projected_new_records"]["semantic_clusters"], 0)
        self.assertEqual(review["projected_new_records"]["semantic_nodes"], 1)
        self.assertEqual(review["projected_new_records"]["semantic_edges"], 2)
        self.assertEqual(self.db.project_state(self.owner, self.project), before)
        self._ingest(packet)
        state = self.db.project_state(self.owner, self.project)
        n = next(v for v in state["semantic_nodes"].values() if v["kind"] == "academic_claim")
        practical = next(v for v in state["semantic_nodes"].values() if v["layer"] == "practical")
        workspace = ProductWorkspace(_MemoryStore(state))
        trace = workspace.trace_node(self.project, practical["id"])
        self.assertEqual(trace["paths"]["academic"], [])
        self.assertEqual(len([e for e in state["semantic_edges"].values()
                              if e["relation"] == "DERIVED_FROM"]), 1)
        self.assertTrue(self.db.preview(self.owner, self.project, packet)["already_imported"])

    def test_forged_quote_or_wrong_doi_is_rejected_not_ingested(self):
        raw = grounding()
        raw["claims"][0]["evidence"][0]["quote"] = "No such quotation in any known abstract."
        before = copy.deepcopy(self.db.project_state(self.owner, self.project))
        with self.assertRaisesRegex(ValueError, "not present"):
            self._convert(raw)
        self.assertEqual(self.db.project_state(self.owner, self.project), before)
        raw = grounding()
        raw["claims"][0]["evidence"][0]["doi"] = "10.9999/foreign.article"
        with self.assertRaisesRegex(ValueError, "DOI not present"):
            self._convert(raw)

    def test_unsupported_and_unjudged_are_never_promoted(self):
        for verdict in ("not_found", "not_run", "error", "contradicted"):
            raw = grounding()
            raw["claims"][0]["verdict"] = verdict
            with self.assertRaisesRegex(ValueError, "no supportable"):
                self._convert(raw)
        raw = grounding()
        raw["claims"][0]["rejected_quotes"] = 1
        with self.assertRaisesRegex(ValueError, "no supportable"):
            self._convert(raw)

    def test_unknown_project_or_missing_literature_is_rejected(self):
        other = self.db.create_project(self.owner,self.tenant["tenant_id"],"Other","No evidence")
        with self.assertRaisesRegex(ValueError, "Nocturnal case module"):
            convert_grounding(grounding(),self.db.project_state(self.owner,other),
                              other,"china-kangmei-2020")

    def test_private_cli_review_enqueue_worker_and_permissions(self):
        p = Path(self.tmp.name)/"result.json"
        p.write_text(json.dumps(grounding()))
        args = ["--db",self.path,"--project",self.project,
                "--candidate","china-kangmei-2020","--ground-json",str(p)]
        token = self.db.issue_token(self.owner)
        with patch.dict(os.environ,{"CITE_REFINERY_TOKEN":token}):
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args+["preview"]),0)
            preview=json.loads(out.getvalue())
            self.assertEqual(preview["grounding_scope"]["supported_abstract_claims"],1)
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args+["enqueue","--expected-revision",
                                     str(preview["review"]["project_revision"]),
                                     "--expected-packet-digest",
                                     preview["review"]["packet_digest"]]),0)
            job=json.loads(out.getvalue())["job_id"]
            self.assertEqual(self.db.run_one_job()["status"],"succeeded")
            self.assertEqual(self.db.get_job(self.owner,job)["status"],"succeeded")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args+["enqueue","--expected-revision","0",
                                         "--expected-packet-digest",
                                         preview["review"]["packet_digest"]]),2)
        with patch.dict(os.environ,{"CITE_REFINERY_TOKEN":"invalid"}):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args+["preview"]),2)


if __name__=="__main__":
    unittest.main()
