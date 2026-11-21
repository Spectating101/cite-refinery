"""Engineering change dossier receiver: hash and identity checks, kept failures, stale editions.

The covered files here are controlled fixtures with the HS and Policy Lab field
shapes the receiver reads. They are not HS output; the real exchange from an HS
replay is exercised by test_engineering_change_real_exchange.py.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.app import CiteRefinery
from cite_refinery.engineering_change_cli import main as cli
from cite_refinery.engineering_change_dossier import (
    ChangeEvidenceRejected, StaleEdition, build_dossier, canonical_bytes, check_currency, issue_dossier,
    OPERATORS, mark_stale_in_workspace, record_in_workspace, render_markdown, verify_change_evidence)

PROJECT = "digital-0123456789abcdef0123456789abcdef"
RUN1, RUN2, RUN3 = "a" * 32, "b" * 32, "c" * 32


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _h(label: str) -> str:
    return _sha(label.encode())


def _checks(runtime_limit: float, runtime_passed: bool, actual: float = 3.166) -> list[dict]:
    return [{"id": "work_runtime", "passed": runtime_passed, "actual": actual, "limit": runtime_limit, "unit": "h"},
            {"id": "supply_margin", "passed": True, "actual": 0.42, "limit": 0.3, "unit": "A"}]


def _export(revision, run_id, parent, requirements, checks, package):
    return {"schema": "hardware_splicer.policy_evidence.v1", "project_id": PROJECT, "revision": revision,
            "run_id": run_id, "physical_authority_granted": False, "package": {"path": "STUDY.zip", "sha256": package},
            "study": {"revision": revision, "run_id": run_id, "parent_revision": parent,
                      "summary": {"requirements": requirements, "constraints": checks,
                                  "requirements_met": all(c["passed"] for c in checks)}}}


def _identity(revision, run_id, parent, requirements, checks, tag):
    return {"revision": revision, "run_id": run_id, "parent_revision": parent, "change_request": f"r{revision}",
            "case_id": "fielddeck-5", "snapshot_sha256": _h("snap" + tag), "seal_sha256": _h("seal" + tag),
            "package_sha256": _h("pkg" + tag), "calculation": "analysis/calculations.json",
            "calculation_sha256": _h("calc" + tag), "requirements": requirements,
            "requirements_met": all(c["passed"] for c in checks), "checks": checks}


def _receipt(review: dict, review_bytes: bytes) -> dict:
    return {"schema": "policylab.hardware_policy_verification.v1", "verified": True,
            "source_binding": review["source_binding"], "decision": review["decision"],
            "physical_authority_granted": False, "review_sha256": _sha(review_bytes)}


class Exchange:
    """Writes one consistent controlled exchange and the matching packet."""

    def __init__(self, root: Path, *, candidate_review=True, design_candidate=False):
        self.root = root
        r1 = {"minimum_work_runtime_h": 2.5, "minimum_supply_margin_a": 0.3, "pi_work_current_a": 1.0}
        r2 = {**r1, "minimum_work_runtime_h": 4.0}
        r2_checks = _checks(4.0, False)
        if design_candidate:
            r2["pi_work_current_a"] = 0.697
            r2_checks = _checks(4.0, True, 4.002)
        self.base = _identity(1, RUN1, None, r1, _checks(2.5, True), "1")
        self.candidate = _identity(2, RUN2, 1, r2, r2_checks, "2")
        files = {"base_export": _export(1, RUN1, None, r1, _checks(2.5, True), self.base["package_sha256"]),
                 "candidate_export": _export(2, RUN2, 1, r2, r2_checks, self.candidate["package_sha256"])}
        files["candidate_export"]["study"]["summary"]["metrics"] = {"work_runtime_lower_h": r2_checks[0]["actual"]}
        raw = {role: canonical_bytes(value) for role, value in files.items()}
        review = {"schema": "policylab.hardware_policy_review.v1", "physical_authority_granted": False,
                  "decision": "BLOCKED", "policy": {"id": "portable-runtime-4h", "version": "1.0.0"},
                  "source_binding": {"evidence_sha256": _sha(raw["base_export"]), "project_id": PROJECT,
                                     "revision": 1, "run_id": RUN1},
                  "unmet_constraints": [{"id": "work-runtime", "fact": "metric.work_runtime_lower_h", "operator": ">=",
                                         "value": 4, "unit": "h", "actual": 3.166}],
                  "target_results": [{"id": "work-runtime", "fact": "metric.work_runtime_lower_h", "operator": ">=",
                                      "value": 4, "unit": "h", "actual": 3.166, "passed": False}],
                  "revision_requirements": {"minimum_work_runtime_h": 4}}
        row = {"id": "pi-work-load-budget", "kind": "modelled_candidate_design_change", "status": "PROPOSED",
               "target": "work-runtime", "input": "pi_work_current_a", "before": 1.0, "after": 0.697,
               "requirement_overrides": {"pi_work_current_a": 0.697}, "model": "runtime_inverse_to_work_power",
               "formula": "P_required = E_min / T", "numbers": {"runtime_h": 3.166}, "assumptions": ["linear"],
               "basis": "controlled fixture"}
        if design_candidate:
            review["candidate_design_changes"] = [row]
        files["base_review"], raw["base_review"] = review, canonical_bytes(review)
        files["base_review_replay"] = _receipt(review, raw["base_review"])
        raw["base_review_replay"] = canonical_bytes(files["base_review_replay"])
        proposal = {"schema": "hardware_splicer.policy_feedback_proposal.v1", "source_binding": review["source_binding"],
                    "policy_review_sha256": _sha(raw["base_review"]), "project_id": PROJECT, "base_revision": 1,
                    "revision_requirements": {"minimum_work_runtime_h": 4}, "resolved_requirements": r2,
                    "requirement_changes": {"minimum_work_runtime_h": {"before": 2.5, "after": 4.0}},
                    "automatic_execution": False, "physical_authority_granted": False,
                    "policy_review_replay_sha256": _sha(raw["base_review_replay"]),
                    "applied_candidates": [row] if design_candidate else [],
                    "candidate_overrides": dict(row["requirement_overrides"]) if design_candidate else {}}
        if design_candidate:
            proposal["requirement_changes"]["pi_work_current_a"] = {"before": 1.0, "after": 0.697}
        files["proposal"], raw["proposal"] = proposal, canonical_bytes(proposal)
        if candidate_review:
            again = deepcopy(review)
            again["source_binding"] = {"evidence_sha256": _sha(raw["candidate_export"]), "project_id": PROJECT,
                                       "revision": 2, "run_id": RUN2}
            files["candidate_review"], raw["candidate_review"] = again, canonical_bytes(again)
            files["candidate_review_replay"] = _receipt(again, raw["candidate_review"])
            raw["candidate_review_replay"] = canonical_bytes(files["candidate_review_replay"])
        self.records = {}
        for role, data in raw.items():
            (root / f"{role}.json").write_bytes(data)
            self.records[role] = {"path": f"{role}.json", "schema": files[role]["schema"], "sha256": _sha(data),
                                  "bytes": len(data)}
        self.packet = {
            "schema": "hardware_splicer.engineering_change_evidence.v1", "source_project": "hardware-splicer",
            "project_id": PROJECT, "case_id": "fielddeck-5", "authority_level": "modeled",
            "evidence_kind": "digital_design", "physical_authority_granted": False,
            "objective": {"statement": "Declared design requirements.", "base_requirements": r1,
                          "candidate_requirements": r2, "change_request": "r2"},
            "base": self.base, "candidate": self.candidate,
            "proposal": {"policy_id": "portable-runtime-4h", "policy_version": "1.0.0", "policy_decision": "BLOCKED",
                         "policy_review_sha256": _sha(raw["base_review"]),
                         "revision_requirements": {"minimum_work_runtime_h": 4},
                         "requirement_changes": proposal["requirement_changes"],
                         "unmet_targets": [{"target": "work-runtime", "fact": "metric.work_runtime_lower_h",
                                            "actual": 3.166, "required": ">= 4 h", "reason": None}],
                         "applied_as_revision": 2,
                         "candidate_design_changes": [] if not design_candidate else [{
                             **{key: row[key] for key in ("id", "input", "before", "after", "requirement_overrides",
                                                          "model", "formula", "numbers", "assumptions", "basis")},
                             "label": "Modelled candidate design change", "physical_means": "unknown / not tested",
                             "native_outcome": {"target": "work-runtime", "fact": "metric.work_runtime_lower_h",
                                                "operator": ">=", "required": 4, "unit": "h",
                                                "native_value": 4.002, "met": True}}]},
            "check_delta": {
                "changed_dependencies": [{"dependency_id": "requirement:minimum_work_runtime_h",
                                          "before": 2.5, "after": 4.0}],
                "stale": [{"check": "work_runtime", "status": "invalidated", "from_revision": 1, "run_id": RUN1,
                           "result": _checks(2.5, True)[0], "rerun": None, "reasons": [],
                           "counts_for_candidate": False}],
                "retained": [{"check": "supply_margin", "status": "retained", "from_revision": 1, "run_id": RUN1,
                              "result": _checks(2.5, True)[1], "rerun": None, "reasons": [],
                              "counts_for_candidate": True}],
                "blocked": [], "rerun": [], "stale_counted_as_passing": False},
            "unresolved": [] if design_candidate else [
                {"kind": "failing_check", "check": "work_runtime", "revision": 2, "run_id": RUN2,
                 "actual": 3.166, "limit": 4.0, "unit": "h", "transition": "regressed"}],
            "not_tested": ["No physical build or measurement."], "not_linked": [],
            "head_at_export": {"revision": 2, "run_id": RUN2}, "files": self.records}

    def packet_bytes(self, packet=None) -> bytes:
        return canonical_bytes(packet or self.packet)

    def head(self, identity=None) -> bytes:
        identity = identity or self.candidate
        return canonical_bytes({"schema": "hardware_splicer.revision_head.v1", "source_project": "hardware-splicer",
                                "project_id": PROJECT, "authority_level": "modeled",
                                "physical_authority_granted": False,
                                "head": {key: identity[key] for key in ("revision", "run_id", "parent_revision",
                                                                        "snapshot_sha256", "seal_sha256",
                                                                        "package_sha256", "requirements_met")}})


class EngineeringChangeDossierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.x = Exchange(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def rejected(self, packet=None, match=""):
        with self.assertRaisesRegex(ChangeEvidenceRejected, match):
            build_dossier(self.x.packet_bytes(packet), self.root)

    def test_dossier_keeps_the_failing_check_and_marks_the_earlier_pass_stale(self):
        dossier, currency = issue_dossier(self.x.packet_bytes(), self.root, self.x.head())
        self.assertEqual(currency["status"], "current")
        checks = {row["check"]: row for row in dossier["checks"]}
        self.assertEqual(checks["work_runtime"]["result"], "FAIL")
        self.assertEqual(checks["work_runtime"]["revision"], 2)
        self.assertEqual(checks["work_runtime"]["earlier_result"]["result"], "pass (modeled)")
        self.assertTrue(checks["work_runtime"]["earlier_status"].startswith("stale"))
        self.assertTrue(checks["supply_margin"]["earlier_status"].startswith("retained"))
        self.assertEqual(dossier["physical_authority_granted"], False)
        self.assertEqual(dossier["edition"]["bound_to"]["revision"], 2)
        self.assertEqual(dossier["candidate_policy_review"]["decision"], "BLOCKED")
        text = render_markdown(dossier, currency)
        self.assertIn("**FAIL** 3.166 h against limit 4.0 h", text)
        self.assertIn("FAILING check `work_runtime` in revision 2", text)
        for word in ("ready", "approved", "Ready", "Approved"):
            self.assertNotIn(word, text)
            self.assertNotIn(word, json.dumps(dossier))

    def test_changed_covered_file_is_refused(self):
        path = self.root / "candidate_export.json"
        path.write_bytes(path.read_bytes().replace(b'"passed":false', b'"passed":true'))
        self.rejected(match="does not match its recorded SHA-256")

    def test_recomputed_hash_cannot_hide_a_dropped_failure(self):
        # Rewrite the candidate export so the failure passes, and update the packet hash too.
        export = json.loads((self.root / "candidate_export.json").read_bytes())
        export["study"]["summary"]["constraints"][0]["passed"] = True
        data = canonical_bytes(export)
        (self.root / "candidate_export.json").write_bytes(data)
        packet = deepcopy(self.x.packet)
        packet["files"]["candidate_export"].update(sha256=_sha(data), bytes=len(data))
        self.rejected(packet, "differ from the exported study")
        packet["candidate"]["checks"][0]["passed"] = True
        self.rejected(packet, "review does not bind|unresolved checks differ")

    def test_dropped_unresolved_failure_is_refused(self):
        packet = deepcopy(self.x.packet)
        packet["unresolved"] = []
        self.rejected(packet, "unresolved checks differ")

    def test_revision_identity_mismatch_is_refused(self):
        for key, value in (("revision", 3), ("run_id", RUN3), ("package_sha256", _h("other"))):
            packet = deepcopy(self.x.packet)
            packet["candidate"][key] = value
            self.rejected(packet, "export is not revision|descend")

    def test_proposal_not_applied_is_refused(self):
        packet = deepcopy(self.x.packet)
        proposal = json.loads((self.root / "proposal.json").read_bytes())
        proposal["resolved_requirements"]["minimum_work_runtime_h"] = 3.5
        data = canonical_bytes(proposal)
        (self.root / "proposal.json").write_bytes(data)
        packet["files"]["proposal"].update(sha256=_sha(data), bytes=len(data))
        self.rejected(packet, "resolved requirements")

    def test_physical_authority_or_level_is_refused(self):
        for key, value in (("physical_authority_granted", True), ("authority_level", "physical")):
            packet = deepcopy(self.x.packet)
            packet[key] = value
            self.rejected(packet, "physical")
        packet = deepcopy(self.x.packet)
        packet["objective"]["ready"] = True
        self.rejected(packet, "cannot assert ready")

    def test_stale_counted_check_and_duplicate_keys_are_refused(self):
        packet = deepcopy(self.x.packet)
        packet["check_delta"]["stale"][0]["counts_for_candidate"] = True
        self.rejected(packet, "stale earlier check")
        raw = self.x.packet_bytes().replace(b'{"authority_level"', b'{"authority_level":"modeled","authority_level"', 1)
        with self.assertRaisesRegex(ChangeEvidenceRejected, "duplicate"):
            verify_change_evidence(raw, self.root)

    def test_missing_candidate_review_is_not_linked(self):
        with TemporaryDirectory() as other:
            x = Exchange(Path(other), candidate_review=False)
            dossier = build_dossier(x.packet_bytes(), other)
            self.assertIsNone(dossier["candidate_policy_review"])
            self.assertIn("Candidate Policy Lab review: not linked.", dossier["not_linked"])
            self.assertIn("## Candidate policy review\n\nNot linked.", render_markdown(dossier))

    def test_later_revision_makes_the_edition_stale_and_blocks_reissue(self):
        dossier, _ = issue_dossier(self.x.packet_bytes(), self.root, self.x.head())
        revision3 = {**self.x.candidate, "revision": 3, "run_id": RUN3, "parent_revision": 2,
                     "snapshot_sha256": _h("snap3"), "seal_sha256": _h("seal3"), "package_sha256": _h("pkg3")}
        currency = check_currency(dossier, self.x.head(revision3))
        self.assertEqual(currency["status"], "stale")
        self.assertFalse(currency["reissue_allowed"])
        self.assertIn("HS project is at revision 3", currency["reasons"][0])
        self.assertIn("STALE EDITION", render_markdown(dossier, currency))
        with self.assertRaises(StaleEdition):
            issue_dossier(self.x.packet_bytes(), self.root, self.x.head(revision3))

    def test_changed_hash_at_the_same_revision_is_stale(self):
        dossier, _ = issue_dossier(self.x.packet_bytes(), self.root, self.x.head())
        currency = check_currency(dossier, self.x.head({**self.x.candidate, "package_sha256": _h("rebuilt")}))
        self.assertEqual(currency["status"], "stale")
        self.assertEqual(len(currency["reasons"]), 1)
        self.assertIn("package_sha256 changed", currency["reasons"][0])

    def test_head_for_another_project_is_refused(self):
        dossier, _ = issue_dossier(self.x.packet_bytes(), self.root, self.x.head())
        head = json.loads(self.x.head())
        head["project_id"] = "digital-" + "f" * 32
        with self.assertRaisesRegex(ChangeEvidenceRejected, "another project"):
            check_currency(dossier, canonical_bytes(head))

    def test_workspace_record_uses_cite_claims_and_marks_them_stale(self):
        dossier, _ = issue_dossier(self.x.packet_bytes(), self.root, self.x.head())
        app = CiteRefinery(self.root / "workspace")
        record = record_in_workspace(app, dossier)
        state = app.store.load()
        statuses = {check: state["claims"][claim]["status"] for check, claim in record["claim_ids"].items()}
        self.assertEqual(statuses, {"work_runtime": "modeled_fail", "supply_margin": "modeled_pass"})
        evidence = [row for row in state["evidence"].values() if row["project_id"] == record["project_id"]]
        self.assertEqual({row["provenance"]["sha256"] for row in evidence},
                         {r["sha256"] for r in self.x.records.values()})
        self.assertIn("FAIL", app.dossier_markdown(record["project_id"]))
        revision3 = {**self.x.candidate, "revision": 3, "run_id": RUN3}
        mark_stale_in_workspace(app, record["project_id"], check_currency(dossier, self.x.head(revision3)))
        state = app.store.load()
        self.assertEqual({state["claims"][c]["status"] for c in record["claim_ids"].values()}, {"stale"})

    def test_cli_issues_once_and_reports_stale_with_exit_code(self):
        (self.root / "packet.json").write_bytes(self.x.packet_bytes())
        (self.root / "head2.json").write_bytes(self.x.head())
        (self.root / "head3.json").write_bytes(self.x.head({**self.x.candidate, "revision": 3, "run_id": RUN3}))
        out = self.root / "edition"
        args = ["issue", "--packet", str(self.root / "packet.json"), "--root", str(self.root),
                "--head", str(self.root / "head2.json"), "--out", str(out)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli(args), 0)
            self.assertTrue((out / "dossier.md").is_file())
            self.assertEqual(cli(args), 1)  # an issued edition is never overwritten
            self.assertEqual(cli(["check", "--dossier", str(out / "dossier.json"),
                                  "--head", str(self.root / "head3.json")]), 3)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(cli(["issue", "--packet", str(self.root / "packet.json"), "--root", str(self.root),
                                      "--head", str(self.root / "head3.json"), "--out", str(self.root / "e3")]), 3)
            self.assertEqual(json.loads(buffer.getvalue())["status"], "refused_stale")
        self.assertFalse((self.root / "e3").exists())



class CandidateDesignChangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.x = Exchange(self.root, candidate_review=False, design_candidate=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dossier_shows_candidate_native_outcome_and_unknown_physical_means(self):
        dossier, currency = issue_dossier(self.x.packet_bytes(), self.root, self.x.head())
        [row] = dossier["candidate_design_changes"]
        self.assertEqual(row["native_outcome"]["native_value"], 4.002)
        text = render_markdown(dossier, currency)
        self.assertIn("Physical means of reaching this load: **unknown / not tested**", text)
        self.assertIn("work_runtime_lower_h = **4.002 h**, required >= 4 h: meets the target (modeled, not measured)", text)
        lowered = text.lower() + json.dumps(dossier).lower()
        for word in (r"\bfix(es|ed)?\b", r"\bready\b", r"\bapproved\b"):
            self.assertNotRegex(lowered, word)

    def test_candidate_outcome_or_physical_means_cannot_be_overstated(self):
        for key, value in (("native_value", 4.5), ("met", False)):
            packet = deepcopy(self.x.packet)
            packet["proposal"]["candidate_design_changes"][0]["native_outcome"][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ChangeEvidenceRejected, "native outcome"):
                build_dossier(self.x.packet_bytes(packet), self.root)
        packet = deepcopy(self.x.packet)
        packet["proposal"]["candidate_design_changes"][0]["physical_means"] = "underclock to 1.2 GHz"
        with self.assertRaisesRegex(ChangeEvidenceRejected, "physical means"):
            build_dossier(self.x.packet_bytes(packet), self.root)
        packet = deepcopy(self.x.packet)
        packet["proposal"]["candidate_design_changes"] = []
        with self.assertRaisesRegex(ChangeEvidenceRejected, "differ from those the proposal applied"):
            build_dossier(self.x.packet_bytes(packet), self.root)

    def test_candidate_not_in_the_review_is_refused(self):
        review = json.loads((self.root / "base_review.json").read_bytes())
        review["candidate_design_changes"][0]["after"] = 0.6
        data = canonical_bytes(review)
        (self.root / "base_review.json").write_bytes(data)
        packet = deepcopy(self.x.packet)
        packet["files"]["base_review"].update(sha256=_sha(data), bytes=len(data))
        with self.assertRaises(ChangeEvidenceRejected):
            build_dossier(self.x.packet_bytes(packet), self.root)


class ReviewFindingTests(unittest.TestCase):
    """Refusals added after the 20 November review of the receiver."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.x = Exchange(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def rejected(self, packet, match):
        with self.assertRaisesRegex(ChangeEvidenceRejected, match):
            build_dossier(self.x.packet_bytes(packet), self.root)

    def rewrite(self, role, mutate):
        value = json.loads((self.root / f"{role}.json").read_bytes())
        mutate(value)
        data = canonical_bytes(value)
        (self.root / f"{role}.json").write_bytes(data)
        packet = deepcopy(self.x.packet)
        packet["files"][role].update(sha256=_sha(data), bytes=len(data))
        return packet

    def test_requirements_met_comes_from_the_export(self):
        packet = deepcopy(self.x.packet)
        packet["candidate"]["requirements_met"] = True
        self.rejected(packet, "requirements_met differs")

    def test_proposal_fields_come_from_the_covered_files(self):
        for key, value in (("policy_decision", "PASSED"), ("policy_id", "lenient"), ("policy_version", "9"),
                           ("unmet_targets", []), ("requirement_changes", {}), ("revision_requirements", {})):
            packet = deepcopy(self.x.packet)
            packet["proposal"][key] = value
            with self.subTest(key=key):
                self.rejected(packet, f"packet proposal {key} differs")
        text = render_markdown(build_dossier(self.x.packet_bytes(), self.root))
        self.assertIn("returned **BLOCKED**", text)

    def test_declared_hashes_are_not_part_of_the_verified_identity(self):
        packet = deepcopy(self.x.packet)
        packet["candidate"]["seal_sha256"] = "0" * 64
        dossier = build_dossier(self.x.packet_bytes(packet), self.root)
        self.assertNotIn("seal_sha256", dossier["edition"]["bound_to"])
        self.assertEqual(dossier["declared_by_hs"]["candidate"]["seal_sha256"], "0" * 64)
        self.assertIn("declared by HS, not verified by Cite", render_markdown(dossier))
        # A declared hash that later differs from HS's head still makes the edition stale.
        currency = check_currency(dossier, self.x.head())
        self.assertEqual(currency["status"], "stale")
        self.assertIn("seal_sha256 (declared by HS) changed", currency["reasons"][0])

    def test_ready_or_approved_values_are_refused_but_prose_is_not(self):
        packet = self.rewrite("base_review", lambda r: r.setdefault("assessment", {}).update(status="Approved"))
        self.rejected(packet, "cannot assert status")
        self.x = Exchange(self.root)
        packet = deepcopy(self.x.packet)
        packet["not_tested"] = ["ready"]
        self.rejected(packet, "cannot list 'ready'")
        packet = deepcopy(self.x.packet)
        packet["not_tested"] = ["Not approved for any physical use; nothing is ready."]
        build_dossier(self.x.packet_bytes(packet), self.root)

    def test_reviews_need_receipts_that_bind_their_bytes(self):
        packet = deepcopy(self.x.packet)
        del packet["files"]["candidate_review_replay"]
        self.rejected(packet, "verify receipt")
        packet = self.rewrite("candidate_review_replay", lambda r: r.update(review_sha256="0" * 64))
        self.rejected(packet, "does not bind the review")
        self.x = Exchange(self.root)
        packet = self.rewrite("base_review_replay", lambda r: r.pop("review_sha256"))
        self.rejected(packet, "does not bind the review")

    def test_candidate_review_under_another_policy_is_refused(self):
        def other(review):
            review["policy"]["id"] = "lenient-policy"
        packet = self.rewrite("candidate_review", other)
        receipt = json.loads((self.root / "candidate_review_replay.json").read_bytes())
        receipt["review_sha256"] = packet["files"]["candidate_review"]["sha256"]
        data = canonical_bytes(receipt)
        (self.root / "candidate_review_replay.json").write_bytes(data)
        packet["files"]["candidate_review_replay"].update(sha256=_sha(data), bytes=len(data))
        self.rejected(packet, "different policy")

    def test_a_check_dropped_from_the_candidate_is_shown_untested(self):
        def drop(export):
            export["study"]["summary"]["constraints"] = export["study"]["summary"]["constraints"][:1]
        packet = self.rewrite("candidate_export", drop)
        packet["candidate"]["checks"] = packet["candidate"]["checks"][:1]
        # Rebind the candidate review and its receipt to the changed export bytes.
        sha = packet["files"]["candidate_export"]["sha256"]
        packet2 = self.rewrite("candidate_review", lambda r: r["source_binding"].update(evidence_sha256=sha))
        packet["files"]["candidate_review"] = packet2["files"]["candidate_review"]
        receipt_packet = self.rewrite("candidate_review_replay", lambda r: r.update(
            review_sha256=packet["files"]["candidate_review"]["sha256"],
            source_binding={**r["source_binding"], "evidence_sha256": sha}))
        packet["files"]["candidate_review_replay"] = receipt_packet["files"]["candidate_review_replay"]
        dossier = build_dossier(self.x.packet_bytes(packet), self.root)
        dropped = [row for row in dossier["checks"] if row["result"] == "NOT TESTED"]
        self.assertEqual([row["check"] for row in dropped], ["supply_margin"])
        self.assertIn("1 untested", dossier["decision"]["standing"])

    def test_strict_operators_and_unknown_operators(self):
        with TemporaryDirectory() as other:
            x = Exchange(Path(other), candidate_review=False, design_candidate=True)
            def strict(review):
                review["target_results"][0].update(operator=">", value=4.002)
            review = json.loads((Path(other) / "base_review.json").read_bytes())
            strict(review)
            self.assertIs(OPERATORS[">"](4.002, 4.002), False)
            packet = deepcopy(x.packet)
            packet["proposal"]["candidate_design_changes"][0]["native_outcome"].update(operator=">", required=4.002)
            with self.assertRaises(ChangeEvidenceRejected):
                build_dossier(x.packet_bytes(packet), other)

    def test_missed_candidate_target_must_be_unresolved(self):
        with TemporaryDirectory() as other:
            x = Exchange(Path(other), candidate_review=False, design_candidate=True)
            export = json.loads((Path(other) / "candidate_export.json").read_bytes())
            export["study"]["summary"]["metrics"]["work_runtime_lower_h"] = 3.9
            data = canonical_bytes(export)
            (Path(other) / "candidate_export.json").write_bytes(data)
            packet = deepcopy(x.packet)
            packet["files"]["candidate_export"].update(sha256=_sha(data), bytes=len(data))
            packet["proposal"]["candidate_design_changes"][0]["native_outcome"].update(native_value=3.9, met=False)
            with self.assertRaisesRegex(ChangeEvidenceRejected, "is not unresolved"):
                build_dossier(x.packet_bytes(packet), other)
            packet["unresolved"] = [{"kind": "candidate_target_not_met", "candidate": "pi-work-load-budget"}]
            dossier = build_dossier(x.packet_bytes(packet), other)
            self.assertIn("does NOT meet the target", render_markdown(dossier))

    def test_edited_dossier_identity_cannot_pass_the_stale_gate(self):
        dossier, _ = issue_dossier(self.x.packet_bytes(), self.root, self.x.head())
        forged = deepcopy(dossier)
        forged["edition"]["bound_to"]["revision"] = 3
        forged["edition"]["bound_to"]["run_id"] = RUN3
        with self.assertRaisesRegex(ChangeEvidenceRejected, "edition identity"):
            check_currency(forged, self.x.head({**self.x.candidate, "revision": 3, "run_id": RUN3}))

    def test_malformed_packet_is_a_rejection_not_a_crash(self):
        packet = deepcopy(self.x.packet)
        del packet["candidate"]["checks"]
        packet["candidate"]["requirements"] = None
        self.rejected(packet, "")
        export_packet = self.rewrite("candidate_export", lambda e: e["study"].pop("summary"))
        self.rejected(export_packet, "")

    def test_cli_check_writes_a_new_directory_and_marks_the_workspace(self):
        (self.root / "packet.json").write_bytes(self.x.packet_bytes())
        (self.root / "head2.json").write_bytes(self.x.head())
        (self.root / "head3.json").write_bytes(self.x.head({**self.x.candidate, "revision": 3, "run_id": RUN3}))
        edition, workspace = self.root / "edition", self.root / "workspace"
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cli(["issue", "--packet", str(self.root / "packet.json"), "--root", str(self.root),
                                  "--head", str(self.root / "head2.json"), "--out", str(edition),
                                  "--workspace", str(workspace)]), 0)
        cite_project = json.loads(out.getvalue())["workspace_record"]["project_id"]
        issued = (edition / "dossier.md").read_bytes()
        check = ["check", "--dossier", str(edition / "dossier.json"), "--head", str(self.root / "head3.json"),
                 "--out", str(edition)]
        outputs = []
        for _ in range(2):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(cli(check), 3)
            outputs.append(json.loads(buffer.getvalue())["out"])
        self.assertNotEqual(outputs[0], outputs[1])
        self.assertEqual((edition / "dossier.md").read_bytes(), issued)
        self.assertIn("STALE EDITION", (Path(outputs[0]) / "dossier.md").read_text())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli(check + ["--workspace", str(workspace)]), 1)
            self.assertEqual(cli(check + ["--workspace", str(workspace), "--cite-project-id", PROJECT]), 1)
            self.assertEqual(cli(check + ["--workspace", str(workspace), "--cite-project-id", cite_project]), 3)
        state = CiteRefinery(workspace).store.load()
        self.assertEqual({c["status"] for c in state["claims"].values() if c["project_id"] == cite_project}, {"stale"})


if __name__ == "__main__":
    unittest.main()
