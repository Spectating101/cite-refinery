"""Nocturnal -> Cite-Refinery private practical-layer adapter contract tests.

All CI data is synthetic. Real China case sources stay in Nocturnal's repo and
are read from its frozen empirical commit only during authorized local runs.
"""
import copy
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cite_refinery.hosted_store import WorkspaceDB
from cite_refinery.nocturnal_bridge import (
    CASE_ROOT, FREEZE_PATH, case_to_semantic_packet, load_frozen_china_case,
)
from cite_refinery.nocturnal_bridge_cli import main


def case():
    return {
        "schema": "nocturnal.trace5_empirical_case.v1",
        "country": "China", "candidate_id": "china-frozen-case-2020",
        "domain": "corporate_financial", "matter_id": "frozen-test",
        "chain_id": "frozen-chain", "title": "Frozen fictional oversight example",
        "actors": [],
        "claims": [
            {
                "claim": "Agency documented a financial reporting irregularity.",
                "matter_id": "frozen-test", "event_id": "report",
                "observed_at": "2020-01-01", "status_stage": "official",
                "editorial_review_state": "accepted",
                "sources": ["https://example.org/official-review"],
                "event_actor_roles": [{"entity_id": "agency", "role_type": "investigator",
                                       "review_state": "accepted"}],
                "entity_ids": ["agency"], "media_provenance": [],
            },
            {
                "claim": "Agency described a corrective procedure.",
                "matter_id": "frozen-test", "event_id": "repair",
                "observed_at": "2020-05-01", "status_stage": "corrected",
                "editorial_review_state": "accepted",
                "sources": ["https://example.org/correction"],
                "event_actor_roles": [], "entity_ids": [],
                "trace_edges": [
                    {
                        "source_event_id": "report", "target_event_id": "repair",
                        "relation_type": "corrected_by", "review_state": "accepted",
                        "epistemic_state": "observed",
                        "rationale": "Explicitly linked in the reviewed record",
                    }
                ],
            },
            {
                "claim": "Unverified follow-up statement not accepted.",
                "matter_id": "frozen-test", "event_id": "unreviewed",
                "editorial_review_state": "needs_review",
                "sources": ["https://example.org/proposed"],
                "trace_edges": [],
            },
        ],
    }


def freeze(head: str):
    return {
        "schema": "nocturnal.country_programme_freeze.v1",
        "country": "China", "frozen_empirical_head": head,
        "programme_state": "validated_mechanism_study_frozen",
        "paper_scope": "validated_mechanism_study_candidate",
        "national_validation_approved": False,
        "national_prevalence_inference_ready": False,
        "cross_country_comparison_ready": False,
    }


def git(repo: Path, *args):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        stderr=subprocess.DEVNULL, timeout=15,
    ).decode().strip()


class FrozenNocturnalBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "nocturnal"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin",
                        "https://github.com/Spectating101/nocturnal-oversight.git"], check=True)
        path = self.repo / CASE_ROOT / "china-frozen-case-2020.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(case(), ensure_ascii=False))
        git(self.repo, "add", ".")
        self._commit("source")
        self.empirical_head = git(self.repo, "rev-parse", "HEAD")
        p = self.repo / FREEZE_PATH
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(freeze(self.empirical_head)))
        git(self.repo, "add", ".")
        self._commit("freeze")
        self.dbfile = self.root / "private.sqlite3"
        self.db = WorkspaceDB(self.dbfile)
        ids = self.db.create_tenant("Local Lab", "operator")
        self.owner = ids["owner_user_id"]
        self.token = self.db.issue_token(self.owner)
        self.project = self.db.create_project(
            self.owner, ids["tenant_id"], "Frozen case test", "Practical layer bridge")

    def _commit(self, msg):
        subprocess.run(["git", "-C", str(self.repo),
                        "-c", "user.name=Test", "-c", "user.email=test@example.org",
                        "commit", "-qm", msg], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _convert(self):
        return case_to_semantic_packet(
            *load_frozen_china_case(self.repo, "china-frozen-case-2020")
        )

    def test_exact_frozen_source_and_practical_only_packet(self):
        packet = self._convert()
        self.assertEqual(packet["schema"], "cite_refinery.semantic_graph.v1")
        self.assertEqual([n["layer"] for n in packet["nodes"]],
                         ["neutral", "practical", "practical"])
        self.assertEqual(len(packet["clusters"]), 1)
        self.assertEqual(len(packet["edges"]), 3)
        trace = next(e for e in packet["edges"] if e["relation"].startswith("NOCTURNAL_"))
        self.assertEqual(trace["relation"], "NOCTURNAL_CORRECTED_BY")
        self.assertEqual(trace["status"], "qualified")
        self.assertEqual(trace["provenance"]["review_state"], "accepted")
        self.assertEqual(trace["provenance"]["epistemic_state"], "observed")
        self.assertEqual(packet["conversion_metadata"]["unaccepted_claims_omitted"], 1)
        self.assertFalse(packet["conversion_metadata"]["national_validation_approved"])
        self.assertEqual(packet["conversion_metadata"]["frozen_empirical_commit"], self.empirical_head)
        preview = self.db.preview(self.owner, self.project, packet)
        self.assertEqual(preview["projected_new_records"]["semantic_nodes"], 3)
        self.assertEqual(preview["new_relation_statuses"], {"qualified": 3})
        self.assertFalse(preview["authority_boundary_warnings"])

    def test_uncommitted_worktree_drift_does_not_change_frozen_case(self):
        path = self.repo / CASE_ROOT / "china-frozen-case-2020.json"
        old = self._convert()
        changed = case()
        changed["claims"][0]["claim"] = "Malicious local override"
        path.write_text(json.dumps(changed))
        self.assertEqual(old, self._convert())
        # The importer never reads the modified checkout's case content.
        self.assertNotIn("Malicious local override", json.dumps(self._convert()))

    def test_freeze_manifest_drift_or_wrong_origin_rejected(self):
        manifest = self.repo / FREEZE_PATH
        manifest.write_text(json.dumps(freeze("0"*40)))
        with self.assertRaisesRegex(ValueError, "modified/uncommitted"):
            self._convert()
        manifest.write_text(json.dumps(freeze(self.empirical_head)))
        subprocess.run(["git", "-C", str(self.repo), "remote", "set-url", "origin",
                        "https://github.com/attacker/mirror.git"], check=True)
        with self.assertRaisesRegex(ValueError, "origin"):
            self._convert()

    def test_invalid_case_and_frozen_boundary_rejected(self):
        packet = self._convert()
        c = case()
        case_data, state, identity = load_frozen_china_case(self.repo, "china-frozen-case-2020")
        state["national_validation_approved"] = True
        with self.assertRaisesRegex(ValueError, "boundary"):
            case_to_semantic_packet(c, state, identity)
        c["claims"][0]["sources"] = []
        with self.assertRaisesRegex(ValueError, "lacks original source"):
            case_to_semantic_packet(c, freeze(self.empirical_head), identity)
        c = case()
        c["claims"][1]["trace_edges"][0]["target_event_id"] = "unreviewed"
        with self.assertRaisesRegex(ValueError, "absent/unreviewed"):
            case_to_semantic_packet(c, freeze(self.empirical_head), identity)
        self.assertEqual(packet["conversion_metadata"]["accepted_events_imported"], 2)

    def test_missing_review_state_is_excluded_not_upgraded(self):
        original, frozen, identity = load_frozen_china_case(self.repo, "china-frozen-case-2020")
        modified = copy.deepcopy(original)
        modified["claims"][1].pop("editorial_review_state")
        modified["claims"][1].pop("trace_edges")
        result = case_to_semantic_packet(modified, frozen, identity)
        self.assertEqual(result["conversion_metadata"]["accepted_events_imported"], 1)
        self.assertEqual(result["conversion_metadata"]["unaccepted_claims_omitted"], 2)
        self.assertEqual([node["layer"] for node in result["nodes"]], ["neutral", "practical"])

    def test_independent_cases_have_unique_external_keys_even_when_text_repeats(self):
        first, frozen, identity = load_frozen_china_case(self.repo, "china-frozen-case-2020")
        second = copy.deepcopy(first)
        second["candidate_id"] = "china-other-case-2021"
        second["matter_id"] = "other-case-matter"
        second["title"] = "Other source matter, repeated event statements"
        for claim in second["claims"]:
            claim["matter_id"] = "other-case-matter"
        other_id = {**identity, "case_path":f"{CASE_ROOT}/china-other-case-2021.json"}
        packet1 = case_to_semantic_packet(first, frozen, identity)
        packet2 = case_to_semantic_packet(second, frozen, other_id)
        node_keys1={node["key"] for node in packet1["nodes"]}
        node_keys2={node["key"] for node in packet2["nodes"]}
        self.assertFalse(node_keys1 & node_keys2)
        self.assertNotEqual(packet1["clusters"][0]["key"],packet2["clusters"][0]["key"])

    def test_private_queue_cli_and_worker_idempotence(self):
        args = [
            "--db", str(self.dbfile), "--nocturnal-repo", str(self.repo),
            "--candidate-id", "china-frozen-case-2020",
            "--project", self.project,
        ]
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": self.token}):
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args + ["preview"]), 0)
            review = json.loads(out.getvalue())["review"]
            self.assertEqual(self.db.project_state(self.owner, self.project)["semantic_nodes"], {})
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(
                    main(args + ["enqueue", "--expected-revision", str(review["project_revision"]),
                                 "--expected-packet-digest", review["packet_digest"]]), 0)
            job_id = json.loads(out.getvalue())["job_id"]
        self.assertEqual(self.db.get_job(self.owner, job_id)["status"], "queued")
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")
        atlas = self.db.project_projection(self.owner, self.project)["atlas"]
        self.assertEqual(atlas["summary"]["cluster_count"], 1)
        self.assertEqual(atlas["clusters"][0]["layer_counts"]["practical"], 2)
        self.assertEqual(atlas["clusters"][0]["missing_layers"], ["academic", "program"])
        before = copy.deepcopy(self.db.project_state(self.owner, self.project))
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": self.token}):
            with redirect_stderr(StringIO()):
                self.assertEqual(
                    main(args + ["enqueue", "--expected-revision", "0",
                                 "--expected-packet-digest", review["packet_digest"]]), 2)
        self.assertEqual(self.db.project_state(self.owner, self.project), before)
        self.assertTrue(any(e["action"] == "ingest_committed" for e in
                            self.db.audit_events(self.owner, self.project)))

    def test_missing_or_wrong_bearer_denied(self):
        args = ["--db", str(self.dbfile), "--nocturnal-repo", str(self.repo),
                "--candidate-id", "china-frozen-case-2020", "--project", self.project,
                "preview"]
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": ""}):
            with redirect_stderr(StringIO()):
                self.assertEqual(main(args), 2)
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": "wrong-token"}):
            with redirect_stderr(StringIO()):
                self.assertEqual(main(args), 2)


if __name__ == "__main__":
    unittest.main()
