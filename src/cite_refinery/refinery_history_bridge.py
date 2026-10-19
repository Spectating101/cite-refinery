"""Pinned historical Refinery campaign with cross-scope evidence comparison.

The earlier broad privacy-gate review and later narrow CloakPipe component
evaluation are separate experiments, not comparable pass-rate time series.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .refinery_execution_bridge import load_case as load_narrow, case_to_packet as narrow_packet

SHA = re.compile(r"^[0-9a-f]{40}$")
CASE_ROOT = "evidence/refinery-privacy-gate-20261013"
FILES = (
    "privacy-gate.refinery.json", "overlay.json", "refinery-run.json",
    "eval-esys-watch-results.json", "comparison.json",
)
ORIGINS = {
    "https://github.com/Spectating101/refinery.git",
    "https://github.com/Spectating101/refinery",
    "git@github.com:Spectating101/refinery.git",
}


def _git(repo: Path, *args: str, limit: int = 1000000) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Refinery Git evidence inaccessible") from exc
    if proc.returncode or len(proc.stdout) > limit:
        raise ValueError("pinned Refinery source object missing or excessive")
    return proc.stdout


def _url(pin: str, name: str) -> str:
    return f"https://github.com/Spectating101/refinery/blob/{pin}/{CASE_ROOT}/{name}"


def load_broad(repo: str | Path, commit: str) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(repo).resolve(strict=True)
    if not SHA.fullmatch(commit):
        raise ValueError("explicit source commit required")
    if _git(root, "remote", "get-url", "origin", limit=4096).decode().strip() not in ORIGINS:
        raise ValueError("source repository origin mismatch")
    if _git(root, "cat-file", "-t", commit, limit=50).strip() != b"commit":
        raise ValueError("Refinery pin is not a commit")
    manifest = _git(root, "show", f"{commit}:{CASE_ROOT}/MANIFEST.sha256", limit=24000).decode()
    digests = {}
    for line in manifest.splitlines():
        fields = line.split("  ", 1)
        if len(fields) != 2 or not re.fullmatch(r"[a-f0-9]{64}", fields[0]) or fields[1] in digests:
            raise ValueError("invalid broad-trial manifest")
        digests[fields[1]] = fields[0]
    docs = {}
    hashes = {}
    for name in FILES:
        source = _git(root, "show", f"{commit}:{CASE_ROOT}/{name}")
        h = hashlib.sha256(source).hexdigest()
        if digests.get(name) != h:
            raise ValueError("broad campaign SHA256 mismatch: " + name)
        docs[name] = json.loads(source)
        hashes[name] = h
    return docs, {
        "source_system": "refinery",
        "repository": "Spectating101/refinery",
        "commit": commit, "package": CASE_ROOT,
        "artifact_hashes": hashes,
        "execution_replayed": False,
        "verification_scope": "immutable source artifacts and historical assessment, no test replay",
    }


def broad_packet(bundle: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    if not SHA.fullmatch(str(source.get("commit", ""))):
        raise ValueError("invalid pinned broad-trial source")
    raw = bundle["privacy-gate.refinery.json"]
    commons = raw.get("commons", {})
    caps, implementations, claims = (
        commons.get("capsules", []),
        commons.get("implementations", []),
        commons.get("claims", []),
    )
    if len(caps) != 1 or len(implementations) != 3 or len(claims) != 10:
        raise ValueError("historical inventory changed")
    cap = caps[0]
    if cap.get("key") != "capability:ai-input-sensitive-data-gate":
        raise ValueError("historical capability identity changed")
    decision = bundle["refinery-run.json"].get("evaluate", {})
    d = decision.get("decision", {})
    if (decision.get("capability") != cap["key"]
            or decision.get("component", {}).get("capability", {}).get("maturity") != "implemented"
            or d.get("code") != "REVIEW_REQUIRED"
            or d.get("reuse_candidate") is not False
            or d.get("execution_ready") is not False):
        raise ValueError("historical review outcome or scope altered")
    gaps = bundle["refinery-run.json"].get("gaps", {}).get("open_evidence_gaps")
    if not isinstance(gaps, list) or len(gaps) != 12:
        raise ValueError("open evidence gaps lost")
    if (bundle["overlay.json"].get("predeclared_before_detailed_inspection") is not False
            or len(bundle["overlay.json"].get("projects", [])) != 3):
        raise ValueError("historical three-candidate review was not preregistered")
    subject_pins = {
        "Offsend/Offsend": "4ad97ba7e2c5cfdd52177b235e5d9e34cfecac78",
        "rohansx/cloakpipe": "5186e543056cc59c1f680afe3de2e68514ea89c7",
        "osvaldoC-Dev/ESYS": "a3c19c911e1d6c30da6b48cfbc1292a602055075",
    }
    found = {}
    for item in implementations:
        o = item.get("intrinsic", {}).get("source", {})
        repository = str(o.get("ref", "")).removeprefix("github://")
        if repository in found or subject_pins.get(repository) != o.get("revision"):
            raise ValueError("historical source candidate pin differs")
        found[repository] = item
    if len(found) != 3:
        raise ValueError("historical candidate set incomplete")
    evaluations = [x for x in claims if x.get("intrinsic", {}).get("claim_type") == "evaluation"]
    if len(evaluations) != 1 or evaluations[0]["intrinsic"].get("outcome") != "mixed":
        raise ValueError("mixed evaluation claim absent")
    fixture = bundle["eval-esys-watch-results.json"]
    expected = {"secret": (12, 10), "pii": (8, 7), "clean": (10, 10)}
    if fixture.get("all_passed") is not False:
        raise ValueError("fixture must not be represented as all-pass")
    if any(
        (fixture.get("summary", {}).get(k, {}).get("cases"),
         fixture.get("summary", {}).get(k, {}).get("passed")) != v
        for k, v in expected.items()
    ):
        raise ValueError("detector fixture mixed results changed")
    subj = fixture.get("subject", {})
    if subj.get("repository") != "osvaldoC-Dev/ESYS" or subj.get("revision") != subject_pins["osvaldoC-Dev/ESYS"]:
        raise ValueError("detector evaluation attached to unexpected candidate")
    topic = "refinery-broad-privacy-review-20261013"
    pin = source["commit"]
    nodes, edges = [], []
    def node(key: str, kind: str, statement: str, files: list[str], fields: dict):
        nodes.append({
            "key": key, "kind": kind, "layer": "program",
            "statement": statement, "clusters": [topic],
            "source_refs": [_url(pin, n) for n in files],
            "provenance": {
                **source, **fields,
                "boundary": "Source-recorded campaign assessment, not verified production deployment",
            },
        })
    node("broad-privacy-capability", "capability",
         "Broad AI-input sensitive-data gate is a described capability, not validated end-to-end",
         ["privacy-gate.refinery.json"],
         {"capability_key": cap["key"], "maturity": "implemented"})
    labels = {
        "Offsend/Offsend": "offsend",
        "rohansx/cloakpipe": "cloakpipe",
        "osvaldoC-Dev/ESYS": "esys",
    }
    for repo, label in labels.items():
        impl = found[repo]
        node("historical-" + label, "implementation",
             f"Historical candidate {repo} at {subject_pins[repo][:12]}, not execution approved",
             ["privacy-gate.refinery.json", "overlay.json"],
             {"upstream_repository": repo, "upstream_revision": subject_pins[repo],
              "identity_key": impl["key"]})
        edges.append({
            "source": "historical-" + label, "target": "broad-privacy-capability",
            "relation": "IMPLEMENTS", "status": "qualified",
            "evidence_refs": [_url(pin, "privacy-gate.refinery.json")],
            "provenance": {**source, "boundary": "Source records candidate mapping, not a verified functioning integration"},
        })
    node("esys-mixed-detector-fixture", "outcome",
         "Recorded ESYS fixture: secret 10/12, PII 7/8, clean 10/10; not all passed",
         ["eval-esys-watch-results.json"],
         {"test_summary": fixture["summary"], "all_passed": False, "test_scope": fixture.get("scope")})
    node("broad-twelve-evidence-gaps", "limitation",
         "Broad privacy gate retains twelve unresolved evidence gaps",
         ["refinery-run.json"], {"open_evidence_gaps": gaps, "unresolved_count": 12})
    node("broad-review-required", "outcome",
         "Broad privacy-gate decision: REVIEW_REQUIRED, reuse_candidate=false, execution_ready=false",
         ["refinery-run.json"], {
             "decision": "REVIEW_REQUIRED", "reuse_candidate": False,
             "execution_ready": False, "open_evidence_gaps": 12,
             "reasons": d.get("reasons", []),
         })
    for a, b, rel, f in (
        ("esys-mixed-detector-fixture", "historical-esys", "EVALUATES", "eval-esys-watch-results.json"),
        ("broad-review-required", "broad-twelve-evidence-gaps", "LIMITED_BY", "refinery-run.json"),
        ("broad-review-required", "esys-mixed-detector-fixture", "QUALIFIES", "refinery-run.json"),
    ):
        edges.append({
            "source": a, "target": b, "relation": rel,
            "status": "qualified", "evidence_refs": [_url(pin, f)],
            "provenance": {**source, "boundary": "Observed source review, not approved provider execution"},
        })
    return {
        "schema": "cite_refinery.semantic_graph.v1",
        "source_system": "refinery_history",
        "clusters": [{
            "key": topic,
            "title": "Broad privacy gate candidate review (October 13, 2026)",
            "provenance": {**source, "scope": "three candidate source reviews, one mixed detector fixture"},
        }],
        "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "profile": "broad_privacy_review_20261013",
            "candidate_count": 3, "open_gaps": 12,
            "decision": "REVIEW_REQUIRED", "execution_ready": False,
            "esys_fixture_passed": 27, "esys_fixture_total": 30,
            "boundary": "Broad review and mixed detector fixture, not a preregistered end-to-end privacy test",
        },
    }


def history_comparison(
    broad: dict[str, Any], broad_source: dict[str, Any],
    narrow: dict[str, Any], narrow_source: dict[str, Any],
    project_state: dict[str, Any], project_id: str,
) -> dict[str, Any]:
    """Join source-pinned *different* review scopes without false uplift."""
    earlier = broad_packet(broad, broad_source)
    later = narrow_packet(narrow, narrow_source)
    if (broad_source.get("repository") != narrow_source.get("repository")
            or broad_source.get("commit") != narrow_source.get("refinery_commit")):
        raise ValueError("Refinery campaign sources must have identical pinned commits")
    expected = narrow_source["refinery_commit"]
    keys = {"refinery:program-implementation", "refinery:program-reuse-review"}
    prior = {}
    for obj in project_state.get("semantic_nodes", {}).values():
        if obj.get("project_id") != project_id or obj.get("external_key") not in keys:
            continue
        if not any(
            p.get("source_system") == "refinery"
            and p.get("refinery_commit") == expected
            and p.get("case_id") == "cloakpipe-core-20261016"
            for p in obj.get("provenance_receipts", [])
        ):
            raise ValueError("existing narrow assessment lacks pinned Refinery provenance")
        if obj["external_key"] in prior:
            raise ValueError("ambiguous existing narrow evidence record")
        prior[obj["external_key"]] = obj
    if set(prior) != keys:
        raise ValueError("import the exact narrow execution episode before comparing history")
    implementations = broad["privacy-gate.refinery.json"]["commons"]["implementations"]
    old = next(
        (i for i in implementations
         if i.get("intrinsic", {}).get("source", {}).get("ref") == "github://rohansx/cloakpipe"),
        None,
    )
    new = narrow["cloakpipe-core.refinery.json"]["commons"]["implementations"][0]
    old_pin = old.get("intrinsic", {}).get("source", {}).get("revision") if old else None
    new_pin = new.get("intrinsic", {}).get("source", {}).get("revision")
    if old_pin != new_pin or old_pin != "5186e543056cc59c1f680afe3de2e68514ea89c7":
        raise ValueError("both campaigns must share the exact CloakPipe upstream revision")
    topic = "refinery-comparison-different-evaluation-scopes"
    earlier["clusters"].append({
        "key": topic,
        "title": "Refinery evidence-history comparisons and scope changes",
        "provenance": {
            **broad_source,
            "comparison_method": "source_attributed_scope_comparison_not_a_time_series",
        },
    })
    earlier["nodes"].append({
        "key": "scope-comparison-broad-vs-core",
        "kind": "comparison", "layer": "program",
        "statement": (
            "Earlier broad privacy review: REVIEW_REQUIRED, twelve gaps and mixed ESYS fixture. "
            "Later narrow CloakPipe core assessment: twenty-seven required cases pass, four "
            "broad probes leak, REUSE_CANDIDATE but execution blocked. "
            "These are different experiment scopes, not an improvement rate."
        ),
        "clusters": [topic],
        "source_refs": [
            _url(broad_source["commit"], "refinery-run.json"),
            f"https://github.com/Spectating101/refinery/blob/"
            f"{narrow_source['refinery_commit']}/evidence/cloakpipe-core-20261016/refinery-assessment.json",
        ],
        "provenance": {
            **broad_source,
            "earlier_decision": "REVIEW_REQUIRED",
            "later_bounded_decision": "REUSE_CANDIDATE",
            "shared_upstream_revision": old_pin,
            "comparable_population": False,
            "broad_coverage_proven": False,
            "later_execution_ready": False,
            "invalid_inference": [
                "Overall privacy improvement based on different test fixtures",
                "Later bounded success closes all twelve earlier gaps",
                "ESYS detector and CloakPipe core tests have equal denominators",
            ],
        },
    })
    receipt = {
        "source_system": "refinery_history",
        "source_repository": "Spectating101/refinery",
        "refinery_commit": expected,
        "epistemic_boundary": "Only source episode lineage; different test scopes",
    }
    earlier["edges"].extend([
        {
            "source": "scope-comparison-broad-vs-core",
            "target": "broad-review-required",
            "relation": "COMPARES_WITH", "status": "qualified",
            "provenance": {**receipt, "basis": "earlier historical review"},
        },
        {
            "source": "scope-comparison-broad-vs-core",
            "target": prior["refinery:program-reuse-review"]["id"],
            "relation": "COMPARES_WITH", "status": "qualified",
            "provenance": {**receipt, "basis": "later narrowed recorded evaluation"},
        },
        {
            "source": "historical-cloakpipe",
            "target": prior["refinery:program-implementation"]["id"],
            "relation": "SHARES_PINNED_SOURCE", "status": "qualified",
            "provenance": {**receipt, "upstream_repository": "rohansx/cloakpipe",
                           "upstream_revision": old_pin,
                           "boundary": "Same Git revision, different evaluation contract"},
        },
    ])
    earlier["conversion_metadata"].update({
        "profile": "two_episode_scope_comparison_v1",
        "same_upstream_revision": old_pin,
        "cross_episode_links": 3,
        "equivalent_evaluations": False,
        "earlier_decision_superseded": False,
        "comparison_scope": "Broad review and later narrowed recorded component test",
    })
    return earlier
