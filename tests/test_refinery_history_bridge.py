"""Two distinct Refinery evidence episodes must not imply comparative uplift."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cite_refinery.refinery_history_bridge import (
    load_broad, broad_packet, history_comparison, FILES, CASE_ROOT,
)
from cite_refinery.hosted_store import WorkspaceDB


PIN = "2b03ad20f8ab3d55462adb38852855b940194c94"
UPSTREAM = "5186e543056cc59c1f680afe3de2e68514ea89c7"


def sample():
    pins = {
        "Offsend/Offsend": "4ad97ba7e2c5cfdd52177b235e5d9e34cfecac78",
        "rohansx/cloakpipe": UPSTREAM,
        "osvaldoC-Dev/ESYS": "a3c19c911e1d6c30da6b48cfbc1292a602055075",
    }
    return {
        "privacy-gate.refinery.json": {"commons": {
            "capsules": [{"key": "capability:ai-input-sensitive-data-gate"}],
            "implementations": [
                {"key": f"implementation:{k}", "intrinsic": {
                    "source": {"ref": f"github://{k}", "revision": v}
                }} for k, v in pins.items()
            ],
            "claims": [
                {"intrinsic": {"claim_type": "evaluation", "outcome": "mixed"}}
            ] + [
                {"intrinsic": {"claim_type": "review", "outcome": "observed"}}
                for _ in range(9)
            ],
        }},
        "overlay.json": {
            "predeclared_before_detailed_inspection": False,
            "projects": [{}, {}, {}],
        },
        "refinery-run.json": {
            "evaluate": {
                "capability": "capability:ai-input-sensitive-data-gate",
                "component": {"capability": {"maturity": "implemented"}},
                "decision": {
                    "code": "REVIEW_REQUIRED",
                    "reuse_candidate": False, "execution_ready": False,
                    "reasons": ["12 gaps and missing host execution"],
                },
            },
            "gaps": {"open_evidence_gaps": [f"unresolved gap {i}" for i in range(12)]},
        },
        "eval-esys-watch-results.json": {
            "subject": {
                "repository": "osvaldoC-Dev/ESYS",
                "revision": pins["osvaldoC-Dev/ESYS"],
            },
            "all_passed": False,
            "summary": {
                "secret": {"cases": 12, "passed": 10},
                "pii": {"cases": 8, "passed": 7},
                "clean": {"cases": 10, "passed": 10},
            },
            "scope": "synthetic detector fixture, no provider delivery test",
        },
        "comparison.json": {"boundary": "synthetic comparison"},
    }


def metadata():
    return {"source_system": "refinery", "repository": "Spectating101/refinery",
            "commit": PIN, "package": CASE_ROOT, "execution_replayed": False}


class RefineryHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "refinery"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin",
                        "https://github.com/Spectating101/refinery.git"], check=True)
        self.docs = sample()
        directory = self.repo / CASE_ROOT
        directory.mkdir(parents=True)
        import hashlib
        manifest = []
        for file, value in self.docs.items():
            data = json.dumps(value, sort_keys=True).encode()
            (directory / file).write_bytes(data)
            manifest.append(f"{hashlib.sha256(data).hexdigest()}  {file}\n")
        (directory / "MANIFEST.sha256").write_text("".join(manifest))
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test",
                        "-c", "user.email=test@example.org",
                        "commit", "-qm", "freeze historical assessment"], check=True)
        self.head = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True
        ).strip()
        self.db = WorkspaceDB(self.root / "private.sqlite3")
        ids = self.db.create_tenant("Lab", "operator")
        self.uid = ids["owner_user_id"]
        self.project = self.db.create_project(self.uid, ids["tenant_id"],
                                              "History", "Compare evidence scopes")

    def tearDown(self):
        self.tmp.cleanup()

    def test_pinned_manifest_and_worktree_immunity(self):
        b, m = load_broad(self.repo, self.head)
        self.assertEqual(b, self.docs)
        self.assertEqual(len(m["artifact_hashes"]), 5)
        (self.repo / CASE_ROOT / "refinery-run.json").write_text('{"tamper": true}')
        b2, _ = load_broad(self.repo, self.head)
        self.assertEqual(b2, b)
        packet = broad_packet(b, {**metadata(), "commit": self.head})
        self.assertEqual(len(packet["clusters"]), 1)
        self.assertEqual(len(packet["nodes"]), 7)
        self.assertEqual(len(packet["edges"]), 6)
        self.assertEqual(packet["conversion_metadata"]["decision"], "REVIEW_REQUIRED")
        self.assertFalse(packet["conversion_metadata"]["execution_ready"])
        self.assertEqual(packet["conversion_metadata"]["esys_fixture_total"], 30)

    def test_forged_positive_verdict_and_lost_gaps_rejected(self):
        wrong = sample()
        wrong["refinery-run.json"]["evaluate"]["decision"]["code"] = "REUSE_CANDIDATE"
        with self.assertRaisesRegex(ValueError, "review outcome"):
            broad_packet(wrong, metadata())
        wrong = sample()
        wrong["eval-esys-watch-results.json"]["summary"]["pii"]["passed"] = 8
        with self.assertRaisesRegex(ValueError, "mixed results"):
            broad_packet(wrong, metadata())
        wrong = sample()
        wrong["refinery-run.json"]["gaps"]["open_evidence_gaps"] = []
        with self.assertRaisesRegex(ValueError, "gaps"):
            broad_packet(wrong, metadata())
        wrong = sample()
        wrong["overlay.json"]["predeclared_before_detailed_inspection"] = True
        with self.assertRaisesRegex(ValueError, "not preregistered"):
            broad_packet(wrong, metadata())

    def test_requires_existing_pinned_narrow_import_for_comparison(self):
        fake_later = {"cloakpipe-core.refinery.json": {"commons": {
            "implementations": [{"intrinsic": {"source": {"revision": UPSTREAM}}}]
        }}}
        narrow_meta = {"source_system": "refinery", "repository": "Spectating101/refinery",
                       "refinery_commit": PIN}
        with patch("cite_refinery.refinery_history_bridge.narrow_packet", return_value={}):
            with self.assertRaisesRegex(ValueError, "before comparing"):
                history_comparison(sample(), metadata(), fake_later, narrow_meta,
                                   self.db.project_state(self.uid, self.project),
                                   self.project)
        state = self.db.project_state(self.uid, self.project)
        case_receipt = {"source_system": "refinery", "refinery_commit": PIN,
                        "case_id": "cloakpipe-core-20261016"}
        for i, key in enumerate(("refinery:program-implementation", "refinery:program-reuse-review")):
            state["semantic_nodes"][f"existing:{i}"] = {
                "id": f"existing:{i}", "project_id": self.project,
                "external_key": key, "provenance_receipts": [case_receipt],
            }
        with patch("cite_refinery.refinery_history_bridge.narrow_packet", return_value={}):
            packet = history_comparison(
                sample(), metadata(), fake_later, narrow_meta, state, self.project)
        self.assertEqual(len(packet["clusters"]), 2)
        self.assertEqual(len(packet["nodes"]), 8)
        self.assertEqual(len(packet["edges"]), 9)
        self.assertFalse(packet["conversion_metadata"]["equivalent_evaluations"])
        self.assertFalse(packet["conversion_metadata"]["earlier_decision_superseded"])
        self.assertTrue(any(e["relation"] == "SHARES_PINNED_SOURCE"
                            and e["status"] == "qualified" for e in packet["edges"]))
        before = copy.deepcopy(state)
        before["semantic_nodes"]["existing:0"]["provenance_receipts"][0]["refinery_commit"] = "0"*40
        with patch("cite_refinery.refinery_history_bridge.narrow_packet", return_value={}):
            with self.assertRaisesRegex(ValueError, "lacks pinned"):
                history_comparison(sample(), metadata(), fake_later, narrow_meta,
                                   before, self.project)


if __name__ == "__main__":
    unittest.main()
