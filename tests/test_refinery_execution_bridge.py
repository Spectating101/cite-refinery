"""Source-pinned Refinery execution receipts and private ingestion safety."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cite_refinery.hosted_store import WorkspaceDB, _MemoryStore
from cite_refinery.refinery_execution_bridge import BASE, load_case, case_to_packet
from cite_refinery.refinery_execution_cli import main
from cite_refinery.workspace import ProductWorkspace


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class RefineryExecutionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "refinery"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run([
            "git", "-C", str(self.repo), "remote", "add", "origin",
            "https://github.com/Spectating101/refinery.git",
        ], check=True)
        target = self.repo / BASE
        target.mkdir(parents=True)
        self.files = {
            "contract.json": {
                "schema_version": 1, "declared_before_execution": True,
                "repository": "rohansx/cloakpipe",
                "revision": "5186e543056cc59c1f680afe3de2e68514ea89c7",
                "required": ["sensitive strings removed"],
                "excluded": ["unseen secrets"],
                "problem_relation_id": "relation:accepted",
            },
            "cases.json": [
                {"id": f"required-{n}", "kind": "required_redaction"}
                for n in range(24)
            ] + [
                {"id": f"probe-{n}", "kind": "limitation_probe"}
                for n in range(4)
            ],
            "preexecution-sha256.json": {},
            "build-receipt.json": {},
            "results.json": {},
            "problem-evidence.json": {
                "relation": {
                    "relation_id": "relation:accepted", "review_state": "accepted",
                    "source_observation_id": "observation:one",
                    "evidence_text": "Every time sensitive input was sent, something leaked.",
                },
                "observation": {
                    "observation_id": "observation:one",
                    "canonical_url": "https://example.org/review",
                    "text": "Reporter said: Every time sensitive input was sent, something leaked.",
                },
                "reviews": [{"decision": "accepted", "relation_id": "relation:accepted"}],
            },
            "cloakpipe-core.refinery.json": {},
            "refinery-assessment.json": {},
        }
        target.joinpath("harness").mkdir()
        (target / "harness/Cargo.toml").write_text("synthetic manifest")
        (target / "harness/Cargo.lock").write_text("synthetic lock")
        (target / "harness/src").mkdir()
        (target / "harness/src/main.rs").write_text("fn main() {}")
        contract_hash = digest(json.dumps(self.files["contract.json"], sort_keys=True).encode())
        self.bin_hash = "b" * 64
        self.files["results.json"] = {
            "repository": "rohansx/cloakpipe",
            "revision": "5186e543056cc59c1f680afe3de2e68514ea89c7",
            "binary_sha256": self.bin_hash,
            "preexecution_sha256": {},
            "summary": {
                "required_cases": 27, "required_passed": 27,
                "limitation_probes": 4, "limitation_probe_leaks": 4,
                "receiver_requests": 28,
            },
            "bounded_outcome": "pass",
            "cases": [
                {"id": f"required-{n}", "kind": "required_redaction", "passed": True}
                for n in range(24)
            ] + [
                {"id": f"probe-{n}", "kind": "limitation_probe", "passed": False,
                 "leaked_values": [f"synthetic-{n}"]}
                for n in range(4)
            ],
            "malformed_inputs": [
                {"id": f"invalid-{n}", "passed": True}
                for n in range(3)
            ],
            "observed_at": "2026-10-16T00:00:00Z",
        }
        self.files["build-receipt.json"] = {
            "repository": "rohansx/cloakpipe",
            "revision": "5186e543056cc59c1f680afe3de2e68514ea89c7",
            "exit_code": 0, "build_network": False,
            "binary_sha256": self.bin_hash,
            "harness_source_sha256": digest((target / "harness/src/main.rs").read_bytes()),
            "manifest_sha256": digest((target / "harness/Cargo.toml").read_bytes()),
            "cargo_lock_sha256": digest((target / "harness/Cargo.lock").read_bytes()),
        }
        common_cap = "capability:pattern-only-message-redaction"
        impl_key = "implementation:cloakpipe-core:5186e543:harness-v1"
        self.files["cloakpipe-core.refinery.json"] = {
            "commons": {
                "capsules": [{
                    "key": common_cap,
                    "metadata": {"title": "Pattern-only redaction"},
                    "intrinsic": {"constraints": ["not all secrets"]},
                }],
                "implementations": [{
                    "key": impl_key, "capsule_key": common_cap,
                    "metadata": {"title": "Pinned source test wrapper"},
                    "intrinsic": {
                        "source": {"revision": "5186e543056cc59c1f680afe3de2e68514ea89c7"},
                        "runtime": {
                            "binary_sha256": self.bin_hash,
                            "config": {"emails": True},
                        },
                    },
                }],
                "claims": [
                    {"key": "claim:cloakpipe-core:bounded-evaluation",
                     "intrinsic": {"claim_type": "evaluation", "outcome": "pass",
                                   "payload": {"result": self.files["results.json"]["summary"]},
                                   "evidence_ref": ""}},
                    {"key": "claim:cloakpipe-core:limitations-observed",
                     "intrinsic": {"claim_type": "review", "outcome": "observed"}},
                    {"key": "claim:cloakpipe-core:license-file-observed",
                     "intrinsic": {"claim_type": "rights", "outcome": "observed"}},
                ],
            },
        }
        self.files["refinery-assessment.json"] = {
            "scratch_only": True, "production_admission_changed": False,
            "evaluate": {
                "capability": common_cap,
                "component": {"capability": {"maturity": "evaluated"}},
                "decision": {
                    "code": "REUSE_CANDIDATE",
                    "reuse_candidate": True, "execution_ready": False,
                    "reasons": ["No host mapping"],
                },
            },
        }
        self._write_fixture(target)
        self._commit()
        self.commit = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True
        ).strip()
        self.dbfile = Path(self.tmp.name) / "workspace.sqlite3"
        self.db = WorkspaceDB(self.dbfile)
        owner = self.db.create_tenant("Research", "operator")
        self.user = owner["owner_user_id"]
        self.project = self.db.create_project(
            self.user, owner["tenant_id"], "Privacy case", "Measure bounded component",
        )
        self.token = self.db.issue_token(self.user)

    def _write_fixture(self, target):
        # Contract and cases were fixed before execution: their SHA256s are
        # referenced by preexecution and results receipts.
        for name in ("contract.json", "cases.json"):
            (target / name).write_bytes(
                json.dumps(self.files[name], sort_keys=True).encode("utf-8")
            )
        pre = {
            name: digest((target / name).read_bytes())
            for name in ("contract.json", "cases.json")
        }
        pre["harness/Cargo.toml"] = digest((target / "harness/Cargo.toml").read_bytes())
        pre["harness/src/main.rs"] = digest((target / "harness/src/main.rs").read_bytes())
        self.files["preexecution-sha256.json"] = pre
        self.files["results.json"]["preexecution_sha256"] = pre
        for name in ("preexecution-sha256.json", "results.json"):
            (target / name).write_bytes(json.dumps(self.files[name], sort_keys=True).encode("utf-8"))
        result_sha = digest((target / "results.json").read_bytes())
        self.files["cloakpipe-core.refinery.json"]["commons"]["claims"][0]["intrinsic"]["evidence_ref"] = (
            f"evidence/cloakpipe-core-20261016/results.json#sha256={result_sha}"
        )
        for name in ("build-receipt.json", "problem-evidence.json",
                     "cloakpipe-core.refinery.json", "refinery-assessment.json"):
            (target / name).write_bytes(json.dumps(self.files[name], sort_keys=True).encode("utf-8"))
        names = sorted([
            *self.files.keys(),
            "harness/Cargo.toml", "harness/Cargo.lock", "harness/src/main.rs",
        ])
        (target / "SHA256SUMS").write_text(
            "".join(f"{digest((target / name).read_bytes())}  {name}\n" for name in names)
        )

    def _commit(self):
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "-c", "user.name=Test",
             "-c", "user.email=test@example.org", "commit", "-qm", "freeze evidence"],
            check=True,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self):
        return case_to_packet(*load_case(self.repo, self.commit))

    def test_source_verified_packet_and_epistemic_limit(self):
        packet = self.packet()
        self.assertEqual([n["layer"] for n in packet["nodes"]].count("practical"), 1)
        self.assertEqual([n["layer"] for n in packet["nodes"]].count("program"), 6)
        self.assertEqual(len(packet["edges"]), 7)
        self.assertEqual(packet["conversion_metadata"]["required_passed"], 27)
        self.assertEqual(packet["conversion_metadata"]["limitation_probe_leaks"], 4)
        self.assertFalse(packet["conversion_metadata"]["execution_ready"])
        candidates = [e for e in packet["edges"] if e["status"] == "candidate"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["relation"], "PARTIALLY_ADDRESSES")
        self.assertTrue(any("not general" in (n.get("provenance", {}).get("boundary") or "")
                            for n in packet["nodes"] if n["kind"] == "capability"))

    def test_uncommitted_working_file_ignored_and_wrong_origin_rejected(self):
        initial = self.packet()
        (self.repo / BASE / "results.json").write_text("NOT TRUSTED")
        self.assertEqual(self.packet(), initial)
        subprocess.run(["git", "-C", str(self.repo), "remote", "set-url", "origin",
                        "https://github.com/unknown/refinery.git"], check=True)
        with self.assertRaisesRegex(ValueError, "origin"):
            self.packet()

    def test_committed_file_tamper_without_receipt_update_is_rejected(self):
        original = self.repo / BASE / "results.json"
        data = json.loads(original.read_text())
        data["summary"]["limitation_probe_leaks"] = 0
        original.write_text(json.dumps(data, sort_keys=True))
        self._commit()
        next_commit = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True
        ).strip()
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            load_case(self.repo, next_commit)
        # Earlier exact immutable source commit continues to validate.
        self.assertEqual(len(self.packet()["nodes"]), 7)

    def test_unreviewed_problem_or_inconsistent_subject_refused(self):
        original, identity = load_case(self.repo, self.commit)
        altered = copy.deepcopy(original)
        altered["problem-evidence.json"]["relation"]["review_state"] = "proposed"
        with self.assertRaisesRegex(ValueError, "not reviewed"):
            case_to_packet(altered, identity)
        altered = copy.deepcopy(original)
        altered["build-receipt.json"]["binary_sha256"] = "1" * 64
        with self.assertRaisesRegex(ValueError, "build/result"):
            case_to_packet(altered, identity)
        altered = copy.deepcopy(original)
        altered["results.json"]["cases"][0]["id"] = "substituted-after-contract"
        with self.assertRaisesRegex(ValueError, "test-case IDs"):
            case_to_packet(altered, identity)

    def test_falsified_result_or_broader_readiness_is_rejected(self):
        bundle, identity = load_case(self.repo, self.commit)
        result = copy.deepcopy(bundle)
        result["results.json"]["summary"]["limitation_probe_leaks"] = 0
        with self.assertRaisesRegex(ValueError, "outcome"):
            case_to_packet(result, identity)
        result = copy.deepcopy(bundle)
        result["refinery-assessment.json"]["evaluate"]["decision"]["execution_ready"] = True
        with self.assertRaisesRegex(ValueError, "authority boundary"):
            case_to_packet(result, identity)
        result = copy.deepcopy(bundle)
        result["results.json"]["cases"][0]["passed"] = False
        with self.assertRaisesRegex(ValueError, "case-level outcomes"):
            case_to_packet(result, identity)
        result = copy.deepcopy(bundle)
        result["cloakpipe-core.refinery.json"]["commons"]["implementations"][0]["intrinsic"]["runtime"]["binary_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "tested binary"):
            case_to_packet(result, identity)

    def test_reviewed_queue_worker_replay_and_source_authority(self):
        packet = self.packet()
        before = copy.deepcopy(self.db.project_state(self.user, self.project))
        report = self.db.preview(self.user, self.project, packet)
        self.assertEqual(report["projected_new_records"]["semantic_nodes"], 7)
        self.assertEqual(report["projected_new_records"]["semantic_edges"], 7)
        self.assertEqual(len(report["authority_boundary_warnings"]), 1)
        self.assertIn("practical", report["authority_boundary_warnings"][0])
        self.assertEqual(before, self.db.project_state(self.user, self.project))
        self.db.enqueue(self.user, self.project, packet,
                        report["project_revision"], report["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")
        atlas = self.db.project_projection(self.user, self.project)["atlas"]
        self.assertEqual(atlas["clusters"][0]["layer_counts"],
                         {"practical": 1, "academic": 0, "program": 6})
        state = self.db.project_state(self.user, self.project)
        edge = next(e for e in state["semantic_edges"].values() if e["relation"] == "PARTIALLY_ADDRESSES")
        self.assertEqual(edge["status"], "candidate")
        self.assertTrue(self.db.preview(self.user, self.project, packet)["already_imported"])

    def test_exact_repo_snapshot_links_to_run_but_other_revision_does_not(self):
        repo_packet = {
            "schema": "cite_refinery.semantic_graph.v1",
            "source_system": "repository_portfolio",
            "clusters": [{"key": "repo-history", "title": "Git revision records"}],
            "nodes": [{
                "key": "refinery-git", "statement": "Pinned Refinery source tree",
                "kind": "repository", "layer": "program",
                "clusters": ["repo-history"],
                "provenance": {
                    "repository": "Spectating101/refinery",
                    "snapshot_commit": self.commit,
                    "origin_verified": True,
                },
            }],
            "edges": [],
        }
        preview = self.db.preview(self.user, self.project, repo_packet)
        self.db.enqueue(self.user, self.project, repo_packet, 0, preview["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")
        state = self.db.project_state(self.user, self.project)
        bundle, identity = load_case(self.repo, self.commit)
        mapped = case_to_packet(bundle, identity,
                                project_state=state, project_id=self.project)
        self.assertEqual(mapped["conversion_metadata"]["exact_repository_lineage_links"], 1)
        self.assertEqual(len(mapped["edges"]), 8)
        existing = next(node for node in state["semantic_nodes"].values()
                        if node["kind"] == "repository")
        link = next(edge for edge in mapped["edges"]
                    if edge["target"] == existing["id"])
        self.assertEqual(link["status"], "qualified")
        self.assertEqual(link["relation"], "DERIVED_FROM")
        before = copy.deepcopy(state)
        for node in before["semantic_nodes"].values():
            if node["kind"] == "repository":
                node["provenance_receipts"][0]["snapshot_commit"] = "0" * 40
        other = case_to_packet(bundle, identity,
                               project_state=before, project_id=self.project)
        self.assertEqual(other["conversion_metadata"]["exact_repository_lineage_links"], 0)
        self.assertEqual(len(other["edges"]), 7)
        review = self.db.preview(self.user, self.project, mapped)
        self.db.enqueue(self.user, self.project, mapped,
                        review["project_revision"], review["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"], "succeeded")

    def test_authenticated_cli_and_stale_revision(self):
        args = [
            "--db", str(self.dbfile), "--project", self.project,
            "--refinery-repo", str(self.repo), "--ref", self.commit,
        ]
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": self.token}):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args + ["preview"]), 0)
            pre = json.loads(out.getvalue())
            self.assertEqual(pre["source_evidence_scope"]["established_problem_solution_links"], 0)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args + [
                    "enqueue", "--expected-revision",
                    str(pre["review"]["project_revision"]),
                    "--expected-packet-digest", pre["review"]["packet_digest"],
                ]), 0)
            job_id = json.loads(out.getvalue())["job_id"]
            self.assertEqual(self.db.run_one_job()["status"], "succeeded")
            self.assertEqual(self.db.get_job(self.user, job_id)["status"], "succeeded")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args + [
                    "enqueue", "--expected-revision", "0",
                    "--expected-packet-digest", pre["review"]["packet_digest"],
                ]), 2)
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": "invalid"}):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args + ["preview"]), 2)


if __name__ == "__main__":
    unittest.main()
