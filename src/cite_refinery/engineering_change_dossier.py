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
VERIFICATION_SCHEMA = "policylab.hardware_policy_verification.v1"
FILE_SCHEMAS = {"base_export": EXPORT_SCHEMA, "base_review": REVIEW_SCHEMA, "proposal": PROPOSAL_SCHEMA,
                "candidate_export": EXPORT_SCHEMA, "candidate_review": REVIEW_SCHEMA,
                "base_review_replay": VERIFICATION_SCHEMA, "candidate_review_replay": VERIFICATION_SCHEMA}
REQUIRED_FILES = ("base_export", "base_review", "base_review_replay", "proposal", "candidate_export")
OPERATORS = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b, "<=": lambda a, b: a <= b,
             "<": lambda a, b: a < b, "==": lambda a, b: a == b}
ACCEPTED_AUTHORITY = ("modeled", "source_backed")
# Cite checks these against the covered exports. Snapshot and seal hashes are only declared by HS.
VERIFIED_KEYS = ("revision", "run_id", "package_sha256")
DECLARED_KEYS = ("snapshot_sha256", "seal_sha256")
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
# Values that would read as readiness or approval under a status-like key, or as a bare list entry.
_STATUS_KEYS = frozenset({"status", "decision", "state", "verdict", "readiness", "result", "standing"})
_READY_VALUES = frozenset({"ready", "approved", "fabrication_ready", "power_on_ready", "build_ready", "release_ready",
                           "ready_to_build", "ready_for_fabrication", "physically_validated", "authorized"})
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


def _ready_word(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower().replace("-", "_").replace(" ", "_") in _READY_VALUES


def _no_authority(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _AUTHORITY_FLAGS and child is not False:
                raise ChangeEvidenceRejected(f"{where}: digital evidence cannot assert {key}")
            if key in _STATUS_KEYS and _ready_word(child):
                raise ChangeEvidenceRejected(f"{where}: digital evidence cannot assert {key} = {child!r}")
            _no_authority(child, where)
    elif isinstance(value, list):
        for child in value:
            if _ready_word(child):
                raise ChangeEvidenceRejected(f"{where}: digital evidence cannot list {child!r}")
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
    if export["study"]["summary"].get("requirements_met") is not identity.get("requirements_met"):
        raise ChangeEvidenceRejected(f"{role}: packet requirements_met differs from the exported study")


def _bind_review(role: str, review: Mapping[str, Any], export_sha: str, export: Mapping[str, Any],
                 review_sha: str, receipt: Mapping[str, Any]) -> None:
    binding = review.get("source_binding") or {}
    if binding != {"evidence_sha256": export_sha, "project_id": export["project_id"],
                   "revision": export["revision"], "run_id": export["run_id"]}:
        raise ChangeEvidenceRejected(f"{role}: review does not bind the exact export bytes and revision")
    if receipt.get("review_sha256") != review_sha:
        raise ChangeEvidenceRejected(f"{role}: verify receipt does not bind the review")
    if (receipt.get("verified") is not True or receipt.get("source_binding") != binding
            or receipt.get("decision") != review.get("decision") or receipt.get("physical_authority_granted") is not False):
        raise ChangeEvidenceRejected(f"{role}: verify receipt does not verify this review")


def _unmet(row: Mapping[str, Any]) -> dict[str, Any]:
    """The same normalization HS applies to a Policy Lab unmet row."""
    if "operator" in row:
        required, fact = f"{row['operator']} {row['value']} {row['unit']}", row["fact"]
    else:
        required, fact = f"HS limit {row.get('limit')} {row.get('unit')}", "HS engineering check"
    return {"target": row["id"], "fact": fact, "actual": row.get("actual"), "required": required,
            "reason": row.get("reason")}


def _derive_proposal(review: Mapping[str, Any], proposal: Mapping[str, Any], candidate_revision: int) -> dict[str, Any]:
    """Proposal fields Cite states, taken only from the covered review and proposal files."""
    return {"policy_id": review["policy"]["id"], "policy_version": review["policy"]["version"],
            "policy_decision": review["decision"], "policy_review_sha256": proposal["policy_review_sha256"],
            "revision_requirements": proposal["revision_requirements"],
            "requirement_changes": proposal["requirement_changes"],
            "unmet_targets": [_unmet(row) for row in review["unmet_constraints"]],
            "applied_as_revision": candidate_revision}


def verify_change_evidence(packet_bytes: bytes, root: str | Path) -> dict[str, Any]:
    """Recheck every covered file and rederive what the dossier will state from those bytes."""
    try:
        return _verify_change_evidence(packet_bytes, root)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        # A malformed packet or covered file is a rejection, never a crash.
        raise ChangeEvidenceRejected(f"malformed change evidence: {type(exc).__name__}: {exc}") from exc


def _verify_change_evidence(packet_bytes: bytes, root: str | Path) -> dict[str, Any]:
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
        raise ChangeEvidenceRejected("packet must cover the base export, review and its verify receipt, the proposal "
                                     "and the candidate export")
    if ("candidate_review" in files) != ("candidate_review_replay" in files):
        raise ChangeEvidenceRejected("a candidate review must come with its Policy Lab verify receipt")
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
    _bind_review("base_review", value["base_review"], files["base_export"]["sha256"], value["base_export"],
                 files["base_review"]["sha256"], value["base_review_replay"])
    if "candidate_review" in value:
        _bind_review("candidate_review", value["candidate_review"], files["candidate_export"]["sha256"],
                     value["candidate_export"], files["candidate_review"]["sha256"], value["candidate_review_replay"])
        if value["candidate_review"].get("policy", {}).get("id") != value["base_review"].get("policy", {}).get("id"):
            raise ChangeEvidenceRejected("candidate review uses a different policy from the base review")
    proposal, review = value["proposal"], value["base_review"]
    if (proposal.get("source_binding") != review["source_binding"]
            or proposal.get("policy_review_sha256") != files["base_review"]["sha256"]
            or proposal.get("base_revision") != base["revision"] or proposal.get("automatic_execution") is not False
            or proposal.get("revision_requirements") != review.get("revision_requirements")):
        raise ChangeEvidenceRejected("proposal does not bind the base review and revision")
    if proposal.get("policy_review_replay_sha256") != _sha(canonical_bytes(value["base_review_replay"])):
        raise ChangeEvidenceRejected("proposal was not validated against the covered Policy Lab verify receipt")
    if proposal.get("resolved_requirements") != candidate_study["summary"].get("requirements"):
        raise ChangeEvidenceRejected("candidate revision does not carry the proposal's resolved requirements")
    outcomes = _verify_candidates(packet["proposal"].get("candidate_design_changes"), proposal, review,
                                  value["candidate_export"])
    derived = _derive_proposal(review, proposal, candidate["revision"])
    for key, expected in derived.items():
        if packet["proposal"].get(key) != expected:
            raise ChangeEvidenceRejected(f"packet proposal {key} differs from the covered review and proposal")
    for row, outcome in outcomes:
        if outcome["met"] is not True:
            kind = "candidate_target_unknown" if outcome["met"] is None else "candidate_target_not_met"
            if not any(item.get("kind") == kind and item.get("candidate") == row["id"] for item in packet["unresolved"]):
                raise ChangeEvidenceRejected(f"candidate {row['id']} missed or could not report its target but is not unresolved")
    failing = {row["id"] for row in _checks_from_export(value["candidate_export"]) if not row["passed"]}
    reported = {row.get("check") for row in packet["unresolved"] if row.get("kind") == "failing_check"
                and row.get("revision") == candidate["revision"]}
    if failing != reported:
        raise ChangeEvidenceRejected("packet unresolved checks differ from the candidate's failing checks "
                                     f"(exported {sorted(failing)}, reported {sorted(reported)})")
    if any(row.get("counts_for_candidate") is not False for row in packet["check_delta"]["stale"]):
        raise ChangeEvidenceRejected("a stale earlier check is counted for the candidate revision")
    return {"packet": packet, "packet_sha256": _sha(packet_bytes), "files": value, "proposal": derived}


PHYSICAL_MEANS = "unknown / not tested"
_CANDIDATE_COPY = ("input", "before", "after", "requirement_overrides", "model", "formula", "numbers", "assumptions", "basis")


def _verify_candidates(rows: Any, proposal: Mapping[str, Any], review: Mapping[str, Any],
                       candidate_export: Mapping[str, Any]) -> None:
    """Rederive each applied modelled candidate and its native outcome from the covered bytes."""
    applied = proposal.get("applied_candidates") or []
    rows = [] if rows is None else rows  # packets from before candidates carry no such key
    if not isinstance(rows, list) or [row.get("id") for row in rows] != [row.get("id") for row in applied]:
        raise ChangeEvidenceRejected("packet candidate design changes differ from those the proposal applied")
    stated = {row.get("id"): row for row in review.get("candidate_design_changes") or [] if isinstance(row, dict)}
    targets = {row.get("id"): row for row in review.get("target_results") or [] if isinstance(row, dict)}
    overrides, checked = {}, []
    metrics = candidate_export["study"]["summary"].get("metrics") or {}
    for row, used in zip(rows, applied):
        source = stated.get(used.get("id"))
        if source != used or source.get("status") != "PROPOSED":
            raise ChangeEvidenceRejected(f"candidate {used.get('id')!r} is not the proposed row of the Policy Lab review")
        if any(row.get(key) != source.get(key) for key in _CANDIDATE_COPY) or row.get("physical_means") != PHYSICAL_MEANS:
            raise ChangeEvidenceRejected(f"candidate {row.get('id')!r} differs from the review or names a physical means")
        overrides.update(source["requirement_overrides"])
        target = targets.get(source.get("target")) or {}
        outcome = row.get("native_outcome") or {}
        prefix, _, fact = str(target.get("fact", "")).partition(".")
        summary = candidate_export["study"]["summary"]
        if prefix == "requirement":
            value = (summary.get("requirements") or {}).get(fact)
        elif prefix == "metric":
            value = metrics.get(fact, summary.get(fact) if fact in ("mass_g", "mass_margin_g") else None)
        else:
            raise ChangeEvidenceRejected(f"candidate {row.get('id')!r} target fact is not a metric.* or requirement.* fact")
        if target.get("operator") not in OPERATORS:
            raise ChangeEvidenceRejected(f"candidate {row.get('id')!r} target operator is not supported")
        met = None if value is None else OPERATORS[target["operator"]](value, target["value"])
        checked.append((row, outcome))
        if (outcome.get("fact") != target.get("fact") or outcome.get("required") != target.get("value")
                or outcome.get("operator") != target.get("operator") or outcome.get("native_value") != value
                or outcome.get("met") is not met):
            raise ChangeEvidenceRejected(f"candidate {row.get('id')!r} native outcome differs from the candidate export")
    if overrides != (proposal.get("candidate_overrides") or {}):
        raise ChangeEvidenceRejected("proposal candidate overrides differ from its applied candidates")
    return checked


def _identity(revision: Mapping[str, Any]) -> dict[str, Any]:
    return {key: revision[key] for key in VERIFIED_KEYS}


def _declared(revision: Mapping[str, Any]) -> dict[str, Any]:
    return {key: revision[key] for key in DECLARED_KEYS}


def check_currency(dossier: Mapping[str, Any], head_bytes: bytes) -> dict[str, Any]:
    """Compare a dossier edition with HS's current revision head."""
    head = read_json(head_bytes, "revision head")
    if (head.get("schema") != HEAD_SCHEMA or head.get("physical_authority_granted") is not False
            or not isinstance(head.get("head"), dict)):
        raise ChangeEvidenceRejected("unsupported revision head or authority assertion")
    _no_authority(head, "revision head")
    if head.get("project_id") != dossier["project_id"]:
        raise ChangeEvidenceRejected("revision head belongs to another project")
    try:
        bound = dossier["edition"]["bound_to"]
        declared = dossier["declared_by_hs"]["candidate"]
        candidate = dossier["revisions"]["candidate"]
    except (KeyError, TypeError) as exc:
        raise ChangeEvidenceRejected("dossier lacks its edition identity") from exc
    # A dossier file edited to look current fails here rather than passing the gate.
    if (dossier["edition"].get("edition_id") != _sha(canonical_bytes(bound))
            or any(bound.get(key) != candidate.get(key) for key in VERIFIED_KEYS)):
        raise ChangeEvidenceRejected("dossier edition identity does not match its bound revision")
    current = head["head"]
    reasons = []
    if current.get("revision") != bound["revision"]:
        reasons.append(f"HS project is at revision {current.get('revision')}; this edition describes revision "
                       f"{bound['revision']}")
    for key in VERIFIED_KEYS[1:]:
        if current.get(key) != bound[key]:
            reasons.append(f"{key} changed from {bound[key]} to {current.get(key)}")
    for key in DECLARED_KEYS:
        if current.get(key) != declared.get(key):
            reasons.append(f"{key} (declared by HS) changed from {declared.get(key)} to {current.get(key)}")
    return {"schema": CURRENCY_SCHEMA, "edition_id": dossier["edition"]["edition_id"],
            "project_id": dossier["project_id"], "status": "stale" if reasons else "current",
            "bound_to": deepcopy(bound), "head": deepcopy(current), "reasons": reasons,
            "reissue_allowed": not reasons, "head_sha256": _sha(head_bytes)}


def _check_line(row: Mapping[str, Any]) -> str:
    if row.get("actual") is None and row.get("limit") is None:
        return "(no result in this revision)"
    return f"{row['actual']} {row['unit']} against limit {row['limit']} {row['unit']}"


def build_dossier(packet_bytes: bytes, root: str | Path) -> dict[str, Any]:
    verified = verify_change_evidence(packet_bytes, root)
    packet, files = verified["packet"], verified["files"]
    base, candidate = packet["base"], packet["candidate"]
    stale = {row["check"]: row for row in packet["check_delta"]["stale"]}
    retained = {row["check"]: row for row in packet["check_delta"]["retained"]}
    before = {row["id"]: row for row in _checks_from_export(files["base_export"])}
    checks = []
    after_ids = {row["id"] for row in _checks_from_export(files["candidate_export"])}
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
    for check_id, earlier in before.items():
        if check_id not in after_ids:
            # A check the candidate dropped is shown, never silently removed.
            checks.append({"check": check_id, "result": "NOT TESTED", "revision": candidate["revision"],
                           "run_id": candidate["run_id"], "actual": None, "limit": None, "unit": None,
                           "earlier_result": {"revision": base["revision"], "run_id": base["run_id"],
                                              "result": "FAIL" if not earlier["passed"] else "pass (modeled)",
                                              "actual": earlier["actual"], "limit": earlier["limit"],
                                              "unit": earlier["unit"]},
                           "earlier_status": f"absent from revision {candidate['revision']}; its earlier result does not count"})
    candidate_review = files.get("candidate_review")
    proposal = {**verified["proposal"],
                "candidate_design_changes": deepcopy(packet["proposal"].get("candidate_design_changes") or [])}
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
                         f"under policy {proposal['policy_id']} {proposal['policy_version']}?"),
            "standing": ("Not decided by this dossier. Revision "
                         f"{candidate['revision']} has {sum(row['result'] == 'FAIL' for row in checks)} failing and "
                         f"{sum(row['result'] == 'NOT TESTED' for row in checks)} untested modeled check(s) "
                         "and no physical evidence."),
        },
        "objective": packet["objective"],
        "revisions": {"base": _identity(base) | {"requirements_met": base["requirements_met"]},
                      "candidate": _identity(candidate) | {"requirements_met": candidate["requirements_met"],
                                                           "parent_revision": candidate["parent_revision"],
                                                           "change_request": candidate["change_request"]}},
        "proposal": proposal,
        "declared_by_hs": {"meaning": "Snapshot and seal hashes declared by HS; Cite has no covered file to verify them.",
                           "base": _declared(base), "candidate": _declared(candidate)},
        "candidate_design_changes": deepcopy(packet["proposal"].get("candidate_design_changes") or []),
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
            "base and candidate exports match the packet's project, revision, run, package hash, requirements, "
            "requirements_met and checks",
            "each Policy Lab review has a verify receipt naming its exact bytes",
            "the proposal shown (policy, decision, unmet targets, requirement changes) is read from the covered files",
            "the Policy Lab review binds the exact base export bytes",
            "the HS proposal binds that review, and the candidate carries its resolved requirements",
            "every failing candidate check from the export is listed as unresolved",
            "each applied modelled candidate matches its review row, and its native outcome matches the candidate export",
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
              "## Revisions", "", "| | Revision | Run | Package | Requirements met | Snapshot / seal (declared by HS, not verified by Cite) |",
              "|---|---:|---|---|---|---|"]
    for name in ("base", "candidate"):
        row = rev[name]
        declared = dossier["declared_by_hs"][name]
        lines.append(f"| {name} | {row['revision']} | `{row['run_id'][:12]}` | `{row['package_sha256'][:12]}` | "
                     f"{'yes (modeled)' if row['requirements_met'] else 'no'} | "
                     f"`{declared['snapshot_sha256'][:12]}` / `{declared['seal_sha256'][:12]}` |")
    proposal = dossier["proposal"]
    lines += ["", f"Revision {rev['candidate']['revision']} change request: {rev['candidate']['change_request']}", "",
              "## Proposal", "",
              f"Policy Lab policy `{proposal['policy_id']}` {proposal['policy_version']} returned "
              f"**{proposal['policy_decision']}** on revision {rev['base']['revision']}.", ""]
    lines += [f"- Unmet target `{row['target']}`: {row['fact']} = {row['actual']}, required {row['required']}"
              for row in proposal["unmet_targets"]]
    lines += [f"- Proposed `{name}`: {change['before']} → {change['after']}"
              for name, change in sorted(proposal["requirement_changes"].items())]
    for row in dossier.get("candidate_design_changes") or []:
        outcome = row["native_outcome"]
        verdict = ("not reported" if outcome["met"] is None
                   else "meets the target" if outcome["met"] else "does NOT meet the target")
        lines += ["", f"### Modelled candidate design change `{row['id']}`", "",
                  f"- Input `{row['input']}`: {row['before']} → {row['after']} (model `{row['model']}`).",
                  f"- Formula: `{row['formula']}`.",
                  "- Numbers: " + ", ".join(f"{key} = {value}" for key, value in sorted(row["numbers"].items())) + ".",
                  *[f"- Assumption: {item}" for item in row["assumptions"]],
                  f"- Physical means of reaching this load: **{row['physical_means']}**.",
                  f"- Native rerun (revision {rev['candidate']['revision']}): {outcome['fact']} = "
                  f"**{outcome['native_value']} {outcome['unit']}**, required {outcome['operator']} "
                  f"{outcome['required']} {outcome['unit']}: {verdict} (modeled, not measured)."]
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
    matched = [claim for claim in state["claims"].values()
               if claim.get("project_id") == cite_project_id and claim.get("edition_id") == currency["edition_id"]]
    if not matched:
        raise ValueError(f"no claims of edition {currency['edition_id'][:16]} in Cite project {cite_project_id}; "
                         "pass the Cite project id that issue --workspace returned")
    for claim in matched:
        claim["status"] = "stale"
    app.store.save(state)
    app._event(cite_project_id, "engineering_change.edition_stale",
               {"edition_id": currency["edition_id"], "reasons": list(currency["reasons"])})
