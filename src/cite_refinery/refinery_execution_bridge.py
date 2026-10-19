"""Verified pinned Refinery execution *receipts* -> Program semantic map.

This verifies source snapshot integrity and internal evidence consistency; it
does NOT replay external binaries, authenticate authors or certify deployment.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .semantic import SEMANTIC_PACKET_SCHEMA

SHA = re.compile(r"^[0-9a-f]{40}$")
CASE_ID = "cloakpipe-core-20261016"
BASE = f"evidence/{CASE_ID}"
ORIGINS = {
    "https://github.com/Spectating101/refinery.git",
    "https://github.com/Spectating101/refinery",
    "git@github.com:Spectating101/refinery.git",
}
FILES = (
    "contract.json", "cases.json", "results.json",
    "build-receipt.json", "preexecution-sha256.json",
    "problem-evidence.json", "cloakpipe-core.refinery.json",
    "refinery-assessment.json",
)


def _git(repo: Path, *args: str, limit: int = 2_000_000) -> bytes:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True,
            timeout=18, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Refinery Git evidence cannot be accessed") from exc
    if proc.returncode or len(proc.stdout) > limit:
        raise ValueError("pinned Refinery Git source unavailable or oversized")
    return proc.stdout


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _ref(rev: str, name: str) -> str:
    return f"https://github.com/Spectating101/refinery/blob/{rev}/{BASE}/{name}"


def load_case(repo: str | Path, revision: str) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(repo).resolve(strict=True)
    if not SHA.fullmatch(revision):
        raise ValueError("explicit pinned Refinery commit SHA required")
    if _git(root, "remote", "get-url", "origin", limit=4000).decode().strip() not in ORIGINS:
        raise ValueError("Refinery repository origin is not authoritative")
    if _git(root, "cat-file", "-t", revision, limit=50).strip() != b"commit":
        raise ValueError("pinned object must be a commit")
    manifest = _git(root, "show", f"{revision}:{BASE}/SHA256SUMS", limit=6000).decode()
    checksums: dict[str, str] = {}
    for line in manifest.splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            raise ValueError("malformed Refinery SHA256SUMS")
        checksums[parts[1]] = parts[0]
    bundle: dict[str, Any] = {}
    digests: dict[str, str] = {}
    for name in FILES:
        raw = _git(root, "show", f"{revision}:{BASE}/{name}")
        digest = _hash(raw)
        if checksums.get(name) != digest:
            raise ValueError(f"pinned evidence digest mismatch: {name}")
        bundle[name] = json.loads(raw)
        digests[name] = digest
    prehash = bundle["preexecution-sha256.json"]
    if not isinstance(prehash, dict):
        raise ValueError("preexecution snapshot is not an object")
    for name, expected in prehash.items():
        if name not in checksums or checksums[name] != expected:
            raise ValueError("preexecution digest not consistent with pinned source: " + name)
    build = bundle["build-receipt.json"]
    if checksums.get("harness/src/main.rs") != build.get("harness_source_sha256"):
        raise ValueError("harness hash not consistent with pinned build receipt")
    if checksums.get("harness/Cargo.toml") != build.get("manifest_sha256"):
        raise ValueError("Cargo manifest hash not consistent with build receipt")
    if checksums.get("harness/Cargo.lock") != build.get("cargo_lock_sha256"):
        raise ValueError("Cargo lock hash not consistent with build receipt")
    return bundle, {
        "source_system": "refinery",
        "repository": "Spectating101/refinery",
        "refinery_commit": revision,
        "case_path": BASE,
        "case_id": CASE_ID,
        "source_digests": digests,
        "verification_scope": "Git pinned and SHA256SUMS-checked source receipts; no execution replay",
    }


def case_to_packet(
    bundle: dict[str, Any], identity: dict[str, Any], *,
    project_state: dict[str, Any] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    if identity.get("case_id") != CASE_ID or not SHA.fullmatch(str(identity.get("refinery_commit") or "")):
        raise ValueError("unknown pinned Refinery case identity")
    contract = bundle["contract.json"]
    results = bundle["results.json"]
    build = bundle["build-receipt.json"]
    problem = bundle["problem-evidence.json"]
    commons = bundle["cloakpipe-core.refinery.json"]
    assessment = bundle["refinery-assessment.json"]
    prehash = bundle["preexecution-sha256.json"]
    case_decl = bundle["cases.json"]
    if contract.get("schema_version") != 1 or contract.get("declared_before_execution") is not True:
        raise ValueError("Refinery experiment must have a preregistered contract")
    repo = "rohansx/cloakpipe"
    upstream = "5186e543056cc59c1f680afe3de2e68514ea89c7"
    if any(x.get("repository") != repo or x.get("revision") != upstream
           for x in (contract, results, build)):
        raise ValueError("Refinery artifact source revision conflict")
    if (build.get("exit_code") != 0 or build.get("binary_sha256") != results.get("binary_sha256")
            or build.get("build_network") is not False):
        raise ValueError("build/result subject or execution boundary conflict")
    if results.get("preexecution_sha256") != prehash:
        raise ValueError("preexecution hashes differ from results receipt")
    if not isinstance(case_decl, list) or len(case_decl) != 28:
        raise ValueError("declared test-case inventory invalid")
    if [(x.get("id"), x.get("kind")) for x in case_decl] != [
        (x.get("id"), x.get("kind")) for x in results.get("cases", [])
    ]:
        raise ValueError("observed run does not match preregistered test-case IDs")
    for declared, observed in zip(case_decl, results.get("cases", [])):
        for field in ("text", "sensitive"):
            if declared.get(field) != observed.get(field):
                raise ValueError("recorded case inputs differ from predeclared test inputs")
    if (results.get("bounded_outcome") != "pass"
            or results.get("summary", {}).get("required_cases") != 27
            or results["summary"].get("required_passed") != 27
            or results["summary"].get("limitation_probes") != 4
            or results["summary"].get("limitation_probe_leaks") != 4):
        raise ValueError("unexpected bounded test outcome or limitation counts")
    required = [x for x in results.get("cases", []) if x.get("kind") != "limitation_probe"]
    probes = [x for x in results.get("cases", []) if x.get("kind") == "limitation_probe"]
    malformed = results.get("malformed_inputs", [])
    if (len(required) != 24 or len(malformed) != 3 or len(probes) != 4
            or not all(x.get("passed") is True for x in required + malformed)
            or not all(x.get("passed") is False and x.get("leaked_values") for x in probes)):
        raise ValueError("case-level outcomes disagree with summary")
    decision = assessment.get("evaluate", {}).get("decision", {})
    if (assessment.get("scratch_only") is not True
            or assessment.get("production_admission_changed") is not False
            or decision.get("code") != "REUSE_CANDIDATE"
            or decision.get("reuse_candidate") is not True
            or decision.get("execution_ready") is not False):
        raise ValueError("Refinery assessment authority boundary has changed")
    c = commons.get("commons", {})
    capsules, implementations, claims = (c.get(x, []) for x in ("capsules", "implementations", "claims"))
    if len(capsules) != 1 or len(implementations) != 1 or len(claims) != 3:
        raise ValueError("unexpected capability/implementation/evaluation record inventory")
    cap, impl = capsules[0], implementations[0]
    if (impl.get("capsule_key") != cap.get("key")
            or impl.get("intrinsic", {}).get("source", {}).get("revision") != upstream
            or impl["intrinsic"].get("runtime", {}).get("binary_sha256") != results["binary_sha256"]):
        raise ValueError("capability realization does not match tested binary")
    claim_map = {x.get("key"): x for x in claims}
    evaluation = claim_map.get("claim:cloakpipe-core:bounded-evaluation", {}).get("intrinsic", {})
    limitation = claim_map.get("claim:cloakpipe-core:limitations-observed", {}).get("intrinsic", {})
    if (evaluation.get("outcome") != "pass" or evaluation.get("claim_type") != "evaluation"
            or limitation.get("outcome") != "observed" or limitation.get("claim_type") != "review"
            or evaluation.get("payload", {}).get("result") != results["summary"]
            or str(evaluation.get("evidence_ref", "")).split("#sha256=")[-1]
               != identity.get("source_digests", {}).get("results.json")):
        raise ValueError("assessment claims disagree with recorded results")
    if (assessment.get("evaluate", {}).get("capability") != cap["key"]
            or assessment.get("evaluate", {}).get("component", {}).get("capability", {}).get("maturity") != "evaluated"):
        raise ValueError("assessment capability identity or maturity does not match")
    relation = problem.get("relation", {})
    observation = problem.get("observation", {})
    reviews = problem.get("reviews", [])
    if (relation.get("review_state") != "accepted"
            or relation.get("source_observation_id") != observation.get("observation_id")
            or not any(review.get("decision") == "accepted" and review.get("relation_id") == relation.get("relation_id") for review in reviews)
            or contract.get("problem_relation_id") != relation.get("relation_id")):
        raise ValueError("problem source relation not reviewed or no longer bound")
    if observation.get("canonical_url", "").startswith("https://") is False:
        raise ValueError("problem source link must be HTTPS")
    evidence_text = str(relation.get("evidence_text") or "").strip()
    if len(evidence_text) < 20 or evidence_text not in str(observation.get("text") or ""):
        raise ValueError("reviewed source observation excerpt is not present in original post")
    if not contract.get("excluded"):
        raise ValueError("bounded experiment must declare exclusions")
    commit = identity["refinery_commit"]
    refs = {**identity, "upstream_repository": repo, "upstream_revision": upstream,
            "execution_replayed_by_adapter": False, "source_epistemic_scope": "recorded_refinery_experiment"}
    cluster = "refinery-cloakpipe-recorded-privacy-problem"
    links = {
        "problem": _ref(commit, "problem-evidence.json"),
        "contract": _ref(commit, "contract.json"),
        "results": _ref(commit, "results.json"),
        "build": _ref(commit, "build-receipt.json"),
        "evaluation": _ref(commit, "refinery-assessment.json"),
        "commons": _ref(commit, "cloakpipe-core.refinery.json"),
    }
    nodes = [
        {"key": "problem-source-statement", "layer": "practical", "kind": "observation",
         "statement": f"Public author reported a problem when processing sensitive data with LLMs: {evidence_text}",
         "clusters": [cluster], "source_refs": [observation["canonical_url"], links["problem"]],
         "provenance": {**refs, "reviewed_relation_id": relation["relation_id"],
            "review_state": "accepted_as_source_statement",
            "boundary": "A reviewed extraction of a public self-report, not independent verification of actual leaks"}},
        {"key": "program-capability", "layer": "program", "kind": "capability",
         "statement": str(cap.get("metadata", {}).get("title") or cap["key"]),
         "clusters": [cluster], "source_refs": [links["commons"]],
         "provenance": {**refs, "capability_key": cap["key"],
            "constraints": cap["intrinsic"]["constraints"],
            "boundary": "Narrow pattern-redaction capability, not general PII safety"}},
        {"key": "program-implementation", "layer": "program", "kind": "implementation",
         "statement": f"Pin-specific {impl['metadata']['title']} at {upstream[:12]}",
         "clusters": [cluster], "source_refs": [links["commons"], links["build"]],
         "provenance": {**refs, "implementation_key": impl["key"],
            "tested_binary_sha256": results["binary_sha256"],
            "configuration": impl["intrinsic"]["runtime"]["config"],
            "boundary": "Pinned library plus local wrapper; upstream proxy and production provider not evaluated"}},
        {"key": "program-predeclared-contract", "layer": "program", "kind": "requirement",
         "statement": "Predeclared bounded checks and explicit excluded input categories",
         "clusters": [cluster], "source_refs": [links["contract"]],
         "provenance": {**refs, "declared_before_execution": True,
            "required_cases": contract["required"], "excluded": contract["excluded"]}},
        {"key": "program-bounded-run", "layer": "program", "kind": "outcome",
         "statement": "Recorded finite run: 27/27 required checks passed under the pinned wrapper",
         "clusters": [cluster], "source_refs": [links["results"], links["build"]],
         "provenance": {**refs, "required_passed": 27, "required_total": 27,
            "run_timestamp": results.get("observed_at"),
            "bounded_outcome": "pass", "binary_sha256": results["binary_sha256"],
            "boundary": "Source-recorded test outcomes; importer checks receipts but does not rerun the binary"}},
        {"key": "program-limitation-probes", "layer": "program", "kind": "limitation",
         "statement": "All four recorded broader probes leaked: general protection remains unestablished",
         "clusters": [cluster], "source_refs": [links["results"]],
         "provenance": {**refs, "limitation_probes": 4, "limitation_probe_leaks": 4,
            "excluded": contract["excluded"], "boundary": "Failure outside bounded acceptance contract remains material"}},
        {"key": "program-reuse-review", "layer": "program", "kind": "outcome",
         "statement": "Refinery decision: bounded REUSE_CANDIDATE; execution_ready=false; production admission unchanged",
         "clusters": [cluster], "source_refs": [links["evaluation"]],
         "provenance": {**refs, "decision_code": "REUSE_CANDIDATE", "execution_ready": False,
            "scratch_only": True, "reasons": decision.get("reasons", []),
            "boundary": "Eligible for human reuse review only; not licensed clearance or admitted host execution"}},
    ]
    def edge(src: str, dst: str, relation_type: str, status: str, which: str, boundary: str):
        return {
            "source": src, "target": dst, "relation": relation_type,
            "status": status, "evidence_refs": [links[which]],
            "provenance": {**refs, "relation_scope": boundary},
        }
    edges = [
        edge("program-implementation", "program-capability", "IMPLEMENTS", "qualified", "commons",
             "Exact source record declares this implementation of the narrow capability"),
        edge("program-bounded-run", "program-implementation", "EVALUATES", "qualified", "results",
             "Source-recorded component test against a fixed binary"),
        edge("program-bounded-run", "program-predeclared-contract", "EVALUATED_BY", "qualified", "contract",
             "Finite results evaluated against the declared contract"),
        edge("program-implementation", "program-limitation-probes", "LIMITED_BY", "qualified", "results",
             "Documented broad-prompt limitations"),
        edge("program-reuse-review", "program-bounded-run", "DERIVED_FROM", "qualified", "evaluation",
             "Bounded local assessment references recorded run"),
        edge("program-limitation-probes", "program-reuse-review", "QUALIFIES", "qualified", "evaluation",
             "Broad failures constrain any reuse recommendation"),
        edge("program-capability", "problem-source-statement", "PARTIALLY_ADDRESSES", "candidate", "problem",
             "Related to an original problem context, not proven privacy solution"),
    ]
    # Reconcile with existing v0.18 repo-trend mapping only where exact source
    # repository and revision agree. Cross-project/mismatched pins never join.
    repository_lineage = 0
    if project_state is not None:
        if not project_id:
            raise ValueError("project ID required for repository lineage")
        matched = []
        for existing in project_state.get("semantic_nodes", {}).values():
            if (existing.get("project_id") != project_id
                    or existing.get("kind") != "repository"
                    or existing.get("layer") != "program"):
                continue
            if any(
                receipt.get("source_system") == "repository_portfolio"
                and receipt.get("repository") == identity["repository"]
                and receipt.get("snapshot_commit") == commit
                and receipt.get("origin_verified") is True
                for receipt in existing.get("provenance_receipts", [])
            ):
                matched.append(existing)
        if len(matched) > 1:
            raise ValueError("ambiguous pinned Refinery repository identities")
        if matched:
            edges.append({
                "source": "program-reuse-review",
                "target": matched[0]["id"],
                "relation": "DERIVED_FROM",
                "status": "qualified",
                "evidence_refs": [links["evaluation"]],
                "provenance": {**refs, "relation_scope": (
                    "Version-pinned Refinery assessment belongs to exactly this "
                    "verified Git repository snapshot; NOT proof of production execution"
                )},
            })
            repository_lineage = 1
    return {
        "schema": SEMANTIC_PACKET_SCHEMA, "source_system": "refinery",
        "clusters": [{"key": cluster, "title": "LLM sensitive-data exposure and bounded redaction components",
                      "provenance": {**refs, "scope": "one source report plus one finite component evaluation"}}],
        "nodes": nodes, "edges": edges,
        "conversion_metadata": {
            "case_id": CASE_ID, "pinned_commit": commit,
            "practical_source_statements": 1, "program_nodes": 6,
            "required_passed": 27, "required_total": 27,
            "limitation_probes": 4, "limitation_probe_leaks": 4,
            "decision": "REUSE_CANDIDATE", "execution_ready": False,
            "established_problem_solution_links": 0,
            "exact_repository_lineage_links": repository_lineage,
            "boundary": "Pinned evidence verifies source receipts and internal consistency; no independent execution replay, full privacy claim or public adoption",
        },
    }
