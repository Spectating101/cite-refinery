"""Receive a Hardware Splicer engineering change and issue a revision-bound decision dossier.

Input is ``hardware_splicer.engineering_change_evidence.v1``: a base and a
candidate study revision, the Policy Lab review and HS proposal that link them,
the check delta, and the SHA-256 of every file it covers. This receiver does not
trust the packet's own summary. It rereads every covered file, rechecks its
bytes, and rederives the revision identities, the proposal binding and the
candidate's failing checks from those source files.

A dossier edition is bound to one candidate revision (run, snapshot, seal and
package hashes). ``check_currency`` compares an edition with HS's current
revision head; after any further change the edition is stale and
``issue_dossier`` refuses to issue it again.

Everything received is modeled, digital evidence. The receiver refuses a packet
that claims physical authority or a physical evidence level, and the dossier
never describes a revision as ready or approved.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

PACKET_SCHEMA = "hardware_splicer.engineering_change_evidence.v1"
HEAD_SCHEMA = "hardware_splicer.revision_head.v1"
DOSSIER_SCHEMA = "cite_refinery.engineering_change_dossier.v1"
CURRENCY_SCHEMA = "cite_refinery.engineering_change_currency.v1"
EXPORT_SCHEMA = "hardware_splicer.policy_evidence.v1"
REVIEW_SCHEMA = "policylab.hardware_policy_review.v1"
PROPOSAL_SCHEMA = "hardware_splicer.policy_feedback_proposal.v1"
FILE_SCHEMAS = {"base_export": EXPORT_SCHEMA, "base_review": REVIEW_SCHEMA, "proposal": PROPOSAL_SCHEMA,
                "candidate_export": EXPORT_SCHEMA, "candidate_review": REVIEW_SCHEMA}
REQUIRED_FILES = ("base_export", "base_review", "proposal", "candidate_export")
ACCEPTED_AUTHORITY = ("modeled", "source_backed")
IDENTITY_KEYS = ("revision", "run_id", "snapshot_sha256", "seal_sha256", "package_sha256")
_PACKET_FIELDS = {"schema", "source_project", "project_id", "case_id", "authority_level", "evidence_kind",
                  "physical_authority_granted", "objective", "base", "candidate", "proposal", "check_delta",
                  "unresolved", "not_tested", "not_linked", "head_at_export", "files"}
# Any of these set to anything but False is an authority upgrade a digital packet cannot carry.
_AUTHORITY_FLAGS = frozenset({
    "physical_authority_granted", "physical_validation", "physical_validation_performed",
    "fabrication_authorized", "firmware_authorized", "power_on_authorized", "motion_authorized",
    "operational_authorized", "release_authorized", "fabrication_ready", "power_on_ready",
    "ready", "approved", "build_ready",
})
_MAX_BYTES = 16 * 1024 * 1024
_HEX64 = frozenset("0123456789abcdef")


class ChangeEvidenceRejected(ValueError):
    """The packet or a covered file is malformed, altered, unbound or over-claims authority."""


class StaleEdition(RuntimeError):
    """The dossier edition no longer describes HS's current revision."""

    def __init__(self, currency: Mapping[str, Any]):
        super().__init__("; ".join(currency["reasons"]))
        self.currency = dict(currency)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n").encode("utf-8")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ChangeEvidenceRejected("duplicate JSON key: " + key)
        result[key] = value
    return result


def _finite(value: Any) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _finite(child)
    elif isinstance(value, list):
        for child in value:
            _finite(child)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ChangeEvidenceRejected("non-finite number in change evidence")


def _reject_constant(name: str):
    raise ChangeEvidenceRejected("non-finite number in change evidence: " + name)


def read_json(raw: bytes, what: str) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= _MAX_BYTES:
        raise ChangeEvidenceRejected(f"{what}: expected nonempty JSON bytes, at most 16 MiB")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ChangeEvidenceRejected(f"{what}: malformed JSON") from exc
    if not isinstance(value, dict):
        raise ChangeEvidenceRejected(f"{what}: expected a JSON object")
    _finite(value)
    return value


def _no_authority(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _AUTHORITY_FLAGS and child is not False:
                raise ChangeEvidenceRejected(f"{where}: digital evidence cannot assert {key}")
            _no_authority(child, where)
    elif isinstance(value, list):
        for child in value:
            _no_authority(child, where)


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64


def _covered_file(root: Path, role: str, record: Any) -> tuple[bytes, dict]:
    if not isinstance(record, dict) or set(record) != {"path", "schema", "sha256", "bytes"}:
        raise ChangeEvidenceRejected(f"{role}: file record must list path, schema, sha256 and bytes")
    name = record["path"]
    path = PurePosixPath(name) if isinstance(name, str) else None
    if (path is None or not name or path.is_absolute() or ".." in path.parts or "\\" in name
            or not _is_sha(record["sha256"]) or record["schema"] != FILE_SCHEMAS[role]):
        raise ChangeEvidenceRejected(f"{role}: invalid file record")
    try:
        raw = (root / name).read_bytes()
    except OSError as exc:
        raise ChangeEvidenceRejected(f"{role}: covered file {name} is missing") from exc
    if _sha(raw) != record["sha256"] or len(raw) != record["bytes"]:
        raise ChangeEvidenceRejected(f"{role}: {name} does not match its recorded SHA-256; the bytes changed")
    value = read_json(raw, role)
    if value.get("schema") != record["schema"]:
        raise ChangeEvidenceRejected(f"{role}: file schema differs from its record")
    _no_authority(value, role)
    return raw, value


def _checks_from_export(export: Mapping[str, Any]) -> list[dict]:
    return [{"id": row["id"], "passed": row["passed"] is True, "actual": row.get("actual"),
             "limit": row.get("limit"), "unit": row.get("unit")}
            for row in export["study"]["summary"]["constraints"]]


def _bind_export(role: str, export: Mapping[str, Any], project_id: str, identity: Mapping[str, Any]) -> None:
    study = export.get("study") or {}
    if (export.get("project_id") != project_id or export.get("revision") != identity.get("revision")
            or export.get("run_id") != identity.get("run_id") or study.get("revision") != identity.get("revision")
            or (export.get("package") or {}).get("sha256") != identity.get("package_sha256")
            or export.get("physical_authority_granted") is not False):
        raise ChangeEvidenceRejected(f"{role}: export is not revision {identity.get('revision')} of {project_id} "
                                     "with the recorded run and package")
    declared = [{key: row.get(key) for key in ("id", "passed", "actual", "limit", "unit")}
                for row in identity.get("checks") or []]
    if declared != _checks_from_export(export):
        raise ChangeEvidenceRejected(f"{role}: packet check results differ from the exported study")
    if export["study"]["summary"].get("requirements") != identity.get("requirements"):
        raise ChangeEvidenceRejected(f"{role}: packet requirements differ from the exported study")


def _bind_review(role: str, review: Mapping[str, Any], export_sha: str, export: Mapping[str, Any]) -> None:
    binding = review.get("source_binding") or {}
    if binding != {"evidence_sha256": export_sha, "project_id": export["project_id"],
                   "revision": export["revision"], "run_id": export["run_id"]}:
        raise ChangeEvidenceRejected(f"{role}: review does not bind the exact export bytes and revision")


def verify_change_evidence(packet_bytes: bytes, root: str | Path) -> dict[str, Any]:
    """Recheck every covered file and rederive what the dossier will state from those bytes."""
    packet = read_json(packet_bytes, "packet")
    if set(packet) != _PACKET_FIELDS or packet["schema"] != PACKET_SCHEMA:
        raise ChangeEvidenceRejected("unsupported change evidence schema or fields")
    if packet["source_project"] != "hardware-splicer" or packet["evidence_kind"] != "digital_design":
        raise ChangeEvidenceRejected("change evidence must come from a Hardware Splicer digital design")
    if packet["physical_authority_granted"] is not False or packet["authority_level"] not in ACCEPTED_AUTHORITY:
        raise ChangeEvidenceRejected("change evidence claims physical authority or a physical evidence level")
    _no_authority(packet, "packet")
    base, candidate, files = packet["base"], packet["candidate"], packet["files"]
    if not isinstance(files, dict) or any(role not in files for role in REQUIRED_FILES) or set(files) - set(FILE_SCHEMAS):
        raise ChangeEvidenceRejected("packet must cover the base export and review, the proposal and the candidate export")
    if any(not _is_sha(identity.get(key)) for identity in (base, candidate)
           for key in ("snapshot_sha256", "seal_sha256", "package_sha256")):
        raise ChangeEvidenceRejected("revision identity hashes are missing or malformed")
    root = Path(root)
    raw, value = {}, {}
    for role in sorted(files):
        raw[role], value[role] = _covered_file(root, role, files[role])
    project_id = packet["project_id"]
    _bind_export("base_export", value["base_export"], project_id, base)
    _bind_export("candidate_export", value["candidate_export"], project_id, candidate)
    candidate_study = value["candidate_export"]["study"]
    if candidate.get("parent_revision") != base["revision"] or candidate_study.get("parent_revision") != base["revision"]:
        raise ChangeEvidenceRejected("candidate revision does not descend from the base revision")
    _bind_review("base_review", value["base_review"], files["base_export"]["sha256"], value["base_export"])
    if "candidate_review" in value:
        _bind_review("candidate_review", value["candidate_review"], files["candidate_export"]["sha256"],
                     value["candidate_export"])
    proposal, review = value["proposal"], value["base_review"]
    if (proposal.get("source_binding") != review["source_binding"]
            or proposal.get("policy_review_sha256") != files["base_review"]["sha256"]
            or proposal.get("base_revision") != base["revision"] or proposal.get("automatic_execution") is not False
            or proposal.get("revision_requirements") != review.get("revision_requirements")):
        raise ChangeEvidenceRejected("proposal does not bind the base review and revision")
    if proposal.get("resolved_requirements") != candidate_study["summary"].get("requirements"):
        raise ChangeEvidenceRejected("candidate revision does not carry the proposal's resolved requirements")
    failing = {row["id"] for row in _checks_from_export(value["candidate_export"]) if not row["passed"]}
    reported = {row.get("check") for row in packet["unresolved"] if row.get("kind") == "failing_check"
                and row.get("revision") == candidate["revision"]}
    if failing != reported:
        raise ChangeEvidenceRejected("packet unresolved checks differ from the candidate's failing checks "
                                     f"(exported {sorted(failing)}, reported {sorted(reported)})")
    if any(row.get("counts_for_candidate") is not False for row in packet["check_delta"]["stale"]):
        raise ChangeEvidenceRejected("a stale earlier check is counted for the candidate revision")
    return {"packet": packet, "packet_sha256": _sha(packet_bytes), "files": value}


def _identity(revision: Mapping[str, Any]) -> dict[str, Any]:
    return {key: revision[key] for key in IDENTITY_KEYS}


def check_currency(dossier: Mapping[str, Any], head_bytes: bytes) -> dict[str, Any]:
    """Compare a dossier edition with HS's current revision head."""
    head = read_json(head_bytes, "revision head")
    if (head.get("schema") != HEAD_SCHEMA or head.get("physical_authority_granted") is not False
            or not isinstance(head.get("head"), dict)):
        raise ChangeEvidenceRejected("unsupported revision head or authority assertion")
    _no_authority(head, "revision head")
    if head.get("project_id") != dossier["project_id"]:
        raise ChangeEvidenceRejected("revision head belongs to another project")
    bound = dossier["edition"]["bound_to"]
    current = head["head"]
    reasons = []
    if current.get("revision") != bound["revision"]:
        reasons.append(f"HS project is at revision {current.get('revision')}; this edition describes revision "
                       f"{bound['revision']}")
    for key in IDENTITY_KEYS[1:]:
        if current.get(key) != bound[key]:
            reasons.append(f"{key} changed from {bound[key]} to {current.get(key)}")
    return {"schema": CURRENCY_SCHEMA, "edition_id": dossier["edition"]["edition_id"],
            "project_id": dossier["project_id"], "status": "stale" if reasons else "current",
            "bound_to": deepcopy(bound), "head": deepcopy(current), "reasons": reasons,
            "reissue_allowed": not reasons, "head_sha256": _sha(head_bytes)}


def _check_line(row: Mapping[str, Any]) -> str:
    return f"{row['actual']} {row['unit']} against limit {row['limit']} {row['unit']}"


def build_dossier(packet_bytes: bytes, root: str | Path) -> dict[str, Any]:
    verified = verify_change_evidence(packet_bytes, root)
    packet, files = verified["packet"], verified["files"]
    base, candidate = packet["base"], packet["candidate"]
    stale = {row["check"]: row for row in packet["check_delta"]["stale"]}
    retained = {row["check"]: row for row in packet["check_delta"]["retained"]}
    before = {row["id"]: row for row in _checks_from_export(files["base_export"])}
    checks = []
    for row in _checks_from_export(files["candidate_export"]):
        earlier = before.get(row["id"])
        if row["id"] in stale:
            earlier_status = f"stale (revision {base['revision']} result no longer counts)"
        elif row["id"] in retained:
            earlier_status = "retained (inputs unchanged, rerun matches)"
        elif earlier is None:
            earlier_status = "not tested in the base revision"
        else:
            earlier_status = "not linked by the check delta"
        checks.append({"check": row["id"], "result": "FAIL" if not row["passed"] else "pass (modeled)",
                       "revision": candidate["revision"], "run_id": candidate["run_id"],
                       "actual": row["actual"], "limit": row["limit"], "unit": row["unit"],
                       "earlier_result": None if earlier is None else
                       {"revision": base["revision"], "run_id": base["run_id"],
                        "result": "FAIL" if not earlier["passed"] else "pass (modeled)",
                        "actual": earlier["actual"], "limit": earlier["limit"], "unit": earlier["unit"]},
                       "earlier_status": earlier_status})
    candidate_review = files.get("candidate_review")
    bound = {**_identity(candidate), "packet_sha256": verified["packet_sha256"],
             "files": {role: record["sha256"] for role, record in sorted(packet["files"].items())}}
    dossier = {
        "schema": DOSSIER_SCHEMA,
        "project_id": packet["project_id"],
        "case_id": packet["case_id"],
        "authority_level": packet["authority_level"],
        "physical_authority_granted": False,
        "edition": {"edition_id": _sha(canonical_bytes(bound)), "bound_to": bound,
                    "status_at_issue": "current"},
        "decision": {
            "question": (f"Should revision {candidate['revision']} replace revision {base['revision']} "
                         f"under policy {packet['proposal']['policy_id']} {packet['proposal']['policy_version']}?"),
            "standing": ("Not decided by this dossier. Revision "
                         f"{candidate['revision']} has {sum(row['result'] == 'FAIL' for row in checks)} failing "
                         "modeled check(s) and no physical evidence."),
        },
        "objective": packet["objective"],
        "revisions": {"base": _identity(base) | {"requirements_met": base["requirements_met"]},
                      "candidate": _identity(candidate) | {"requirements_met": candidate["requirements_met"],
                                                           "parent_revision": candidate["parent_revision"],
                                                           "change_request": candidate["change_request"]}},
        "proposal": deepcopy(packet["proposal"]),
        "changed_dependencies": deepcopy(packet["check_delta"]["changed_dependencies"]),
        "checks": checks,
        "candidate_policy_review": None if candidate_review is None else {
            "policy_id": candidate_review["policy"]["id"], "decision": candidate_review["decision"],
            "unmet_targets": [row["id"] for row in candidate_review["unmet_constraints"]]},
        "unresolved": deepcopy(packet["unresolved"]),
        "not_tested": list(packet["not_tested"]),
        "not_linked": list(packet["not_linked"]) + (
            ["Candidate Policy Lab review: not linked."] if candidate_review is None else []),
        "sources": deepcopy(packet["files"]),
        "receiver_checks": [
            "every covered file's bytes match its recorded SHA-256",
            "base and candidate exports match the packet's project, revision, run, package hash, requirements and checks",
            "the Policy Lab review binds the exact base export bytes",
            "the HS proposal binds that review, and the candidate carries its resolved requirements",
            "every failing candidate check from the export is listed as unresolved",
        ],
    }
    return dossier


def render_markdown(dossier: Mapping[str, Any], currency: Mapping[str, Any] | None = None) -> str:
    rev = dossier["revisions"]
    lines = [f"# Engineering change dossier: {dossier['project_id']}", "",
             f"Edition `{dossier['edition']['edition_id'][:16]}` · case `{dossier['case_id']}` · "
             f"evidence level **{dossier['authority_level']}** · physical authority granted: **no**", ""]
    if currency is not None and currency["status"] != "current":
        lines += ["> **STALE EDITION.** " + " ".join(currency["reasons"]) + " Do not reuse this dossier.", ""]
    lines += ["## Decision under review", "", dossier["decision"]["question"], "", dossier["decision"]["standing"], "",
              "## Revisions", "", "| | Revision | Run | Snapshot | Package | Requirements met |", "|---|---:|---|---|---|---|"]
    for name in ("base", "candidate"):
        row = rev[name]
        lines.append(f"| {name} | {row['revision']} | `{row['run_id'][:12]}` | `{row['snapshot_sha256'][:12]}` | "
                     f"`{row['package_sha256'][:12]}` | {'yes (modeled)' if row['requirements_met'] else 'no'} |")
    proposal = dossier["proposal"]
    lines += ["", f"Revision {rev['candidate']['revision']} change request: {rev['candidate']['change_request']}", "",
              "## Proposal", "",
              f"Policy Lab policy `{proposal['policy_id']}` {proposal['policy_version']} returned "
              f"**{proposal['policy_decision']}** on revision {rev['base']['revision']}.", ""]
    lines += [f"- Unmet target `{row['target']}`: {row['fact']} = {row['actual']}, required {row['required']}"
              for row in proposal["unmet_targets"]]
    lines += [f"- Proposed `{name}`: {change['before']} → {change['after']}"
              for name, change in sorted(proposal["requirement_changes"].items())]
    lines += ["", "## Checks", "",
              f"| Check | Revision {rev['candidate']['revision']} result | Revision {rev['base']['revision']} result | Earlier result status |",
              "|---|---|---|---|"]
    for row in dossier["checks"]:
        earlier = row["earlier_result"]
        lines.append(f"| {row['check']} | **{row['result']}** {_check_line(row)} | "
                     f"{'not tested' if earlier is None else earlier['result'] + ' ' + _check_line(earlier)} | "
                     f"{row['earlier_status']} |")
    review = dossier["candidate_policy_review"]
    lines += ["", "## Candidate policy review", "",
              "Not linked." if review is None else
              f"Policy `{review['policy_id']}` on revision {rev['candidate']['revision']}: **{review['decision']}**"
              + (f" (unmet: {', '.join(review['unmet_targets'])})" if review["unmet_targets"] else ""), "",
              "## Unresolved", ""]
    for row in dossier["unresolved"]:
        if row["kind"] == "failing_check":
            lines.append(f"- FAILING check `{row['check']}` in revision {row['revision']}: {_check_line(row)} "
                         f"({row['transition']})")
        elif row["kind"] == "policy_target_unmet":
            lines.append(f"- Policy target `{row['target']}` unmet in revision {row['revision']}: "
                         f"{row['fact']} = {row['actual']}, required {row['required']}")
        else:
            lines.append(f"- {row}")
    if not dossier["unresolved"]:
        lines.append("- None reported by HS.")
    lines += ["", "## Not tested", ""] + [f"- {item}" for item in dossier["not_tested"]]
    lines += ["", "## Not linked", ""] + ([f"- {item}" for item in dossier["not_linked"]] or ["- Nothing reported."])
    lines += ["", "## Sources", "", "| Role | File | SHA-256 |", "|---|---|---|"]
    lines += [f"| {role} | `{record['path']}` | `{record['sha256']}` |" for role, record in dossier["sources"].items()]
    lines += ["", "Receiver checks performed:", ""] + [f"- {item}" for item in dossier["receiver_checks"]] + [""]
    return "\n".join(lines)


def issue_dossier(packet_bytes: bytes, root: str | Path, head_bytes: bytes) -> tuple[dict, dict]:
    """Build a dossier and issue it only if HS's head is still the packet's candidate revision."""
    dossier = build_dossier(packet_bytes, root)
    currency = check_currency(dossier, head_bytes)
    if currency["status"] != "current":
        raise StaleEdition(currency)
    return dossier, currency


def record_in_workspace(app, dossier: Mapping[str, Any]) -> dict[str, Any]:
    """Record an issued dossier through Cite-Refinery's project, claim, evidence and artifact store."""
    rev = dossier["revisions"]
    project = app.init_project(
        f"Engineering change {dossier['project_id']} r{rev['base']['revision']}→r{rev['candidate']['revision']}",
        dossier["decision"]["question"])
    claims = {}
    for row in dossier["checks"]:
        claim = app.add_claim(project.id, f"Revision {row['revision']} check {row['check']}: {row['result']} "
                                          f"({_check_line(row)}), modeled")
        claims[row["check"]] = claim.id
    state = app.store.load()
    for row in dossier["checks"]:
        # A modeled check result is neither grounded nor supported; record it as what it is.
        state["claims"][claims[row["check"]]]["status"] = "modeled_fail" if row["result"] == "FAIL" else "modeled_pass"
        state["claims"][claims[row["check"]]]["edition_id"] = dossier["edition"]["edition_id"]
    app.store.save(state)
    for role, record in dossier["sources"].items():
        app.add_evidence(project.id, source="hardware-splicer" if "review" not in role else "policy-lab",
                         locator=record["path"], summary=f"{role} ({record['schema']})",
                         claim_ids=list(claims.values()),
                         provenance={"sha256": record["sha256"], "bytes": record["bytes"],
                                     "edition_id": dossier["edition"]["edition_id"]})
    artifact = app.add_artifact(project.id, name="engineering change dossier", kind=DOSSIER_SCHEMA,
                                description=f"Edition {dossier['edition']['edition_id']}")
    return {"project_id": project.id, "claim_ids": claims, "artifact_id": artifact.id}


def mark_stale_in_workspace(app, cite_project_id: str, currency: Mapping[str, Any]) -> None:
    """Mark an issued edition's claims stale; the earlier record is kept, not rewritten."""
    if currency["status"] != "stale":
        raise ValueError("only a stale currency result can mark an edition stale")
    state = app.store.load()
    for claim in state["claims"].values():
        if claim.get("project_id") == cite_project_id and claim.get("edition_id") == currency["edition_id"]:
            claim["status"] = "stale"
    app.store.save(state)
    app._event(cite_project_id, "engineering_change.edition_stale",
               {"edition_id": currency["edition_id"], "reasons": list(currency["reasons"])})
