"""Pinned Nocturnal TRACE-5 empirical case -> Practical semantic packet.

Nocturnal owns empirical authority; this module does not discover, re-evaluate,
or silently upgrade academic/program conclusions. The frozen input is read
directly from the recorded Git commit, NOT from mutable working-tree data.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .semantic import SEMANTIC_PACKET_SCHEMA

CASE_SCHEMA = "nocturnal.trace5_empirical_case.v1"
FREEZE_SCHEMA = "nocturnal.country_programme_freeze.v1"
FREEZE_PATH = "examples/research/countries/china/programme_freeze_v1.json"
CASE_ROOT = "examples/research/countries/china/cases"
_CANDIDATE = re.compile(r"^china-[a-z0-9-]{3,110}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_REVIEW = {"accepted", "needs_review", "unreviewed", "rejected"}
_EPISTEMIC = {"observed", "attributed", "inferred", "disputed"}
_RELATIONS = {
    "preceded", "cited_by", "relied_on_by", "explicitly_attributed_as_cause_by",
    "contributed_to", "enabled", "amplified", "alleged_to_have_caused",
    "corrected_by", "reversed_by", "superseded_by", "repealed_by", "mitigated_by",
    "restituted_by", "apologized_for_by", "disputed_by", "contradicted_by",
    "supported_by",
}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _source_urls(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("TRACE sources must be a URL list")
    result = []
    for item in values:
        v = _text(item)
        parts = urlsplit(v)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("TRACE sources must be http(s) URLs without credentials")
        if v not in result:
            result.append(v)
    return result


def _blob(repo: Path, revision: str, path: str) -> bytes:
    r = subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"],
        capture_output=True, check=False, timeout=15,
    )
    if r.returncode:
        raise ValueError(f"frozen source object not accessible: {path}")
    if len(r.stdout) > 1_048_576:
        raise ValueError("frozen case exceeds 1 MiB case limit")
    return r.stdout


def load_frozen_china_case(repo: str | Path, candidate_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Use frozen empirical HEAD recorded in the repository's China programme freeze."""
    repo = Path(repo).resolve()
    # The adapter is intentionally pinned to the owner's source repository,
    # rather than trusting an arbitrary local JSON export labelled "nocturnal".
    origin = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    allowed_origins = {
        "https://github.com/Spectating101/nocturnal-oversight.git",
        "https://github.com/Spectating101/nocturnal-oversight",
        "git@github.com:Spectating101/nocturnal-oversight.git",
    }
    if origin.returncode or origin.stdout.strip() not in allowed_origins:
        raise ValueError("Nocturnal Git origin must match the authoritative repository")
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    if head.returncode or not _REVISION.fullmatch(head.stdout.strip()):
        raise ValueError("Nocturnal checkout has no readable source commit")
    if not _CANDIDATE.fullmatch(candidate_id):
        raise ValueError("invalid China candidate ID")
    freeze_file = repo / FREEZE_PATH
    if not freeze_file.is_file():
        raise ValueError("China programme freeze manifest not found")
    freeze_bytes = freeze_file.read_bytes()
    if freeze_bytes != _blob(repo, head.stdout.strip(), FREEZE_PATH):
        raise ValueError("Nocturnal freeze manifest is modified/uncommitted")
    freeze = json.loads(freeze_bytes)
    if freeze.get("schema") != FREEZE_SCHEMA or freeze.get("country") != "China":
        raise ValueError("not the China programme freeze")
    revision = str(freeze.get("frozen_empirical_head") or "")
    if not _REVISION.fullmatch(revision):
        raise ValueError("invalid frozen empirical commit")
    path = f"{CASE_ROOT}/{candidate_id}.json"
    raw = _blob(repo, revision, path)
    case = json.loads(raw)
    if case.get("candidate_id") != candidate_id:
        raise ValueError("case ID does not match requested frozen path")
    return case, freeze, {
        "frozen_commit": revision,
        "freeze_manifest_commit": head.stdout.strip(),
        "case_path": path,
        "case_sha256": hashlib.sha256(raw).hexdigest(),
    }


def case_to_semantic_packet(
    case: dict[str, Any], freeze: dict[str, Any], identity: dict[str, str]
) -> dict[str, Any]:
    if case.get("schema") != CASE_SCHEMA:
        raise ValueError("unsupported Nocturnal case schema")
    if freeze.get("schema") != FREEZE_SCHEMA or freeze.get("country") != "China":
        raise ValueError("invalid China empirical freeze")
    if (freeze.get("programme_state") != "validated_mechanism_study_frozen"
            or freeze.get("paper_scope") != "validated_mechanism_study_candidate"
            or freeze.get("national_validation_approved") is not False
            or freeze.get("national_prevalence_inference_ready") is not False
            or freeze.get("cross_country_comparison_ready") is not False):
        raise ValueError("frozen programme epistemic boundary changed")
    if identity.get("frozen_commit") != freeze.get("frozen_empirical_head"):
        raise ValueError("case source is not bound to frozen empirical commit")
    if case.get("country") != "China":
        raise ValueError("wrong source jurisdiction")
    cid = _text(case.get("candidate_id"))
    if not _CANDIDATE.fullmatch(cid) or identity.get("case_path") != f"{CASE_ROOT}/{cid}.json":
        raise ValueError("unrecognized or non-development China case path")
    for field in ("matter_id", "chain_id", "title", "domain"):
        if not _text(case.get(field)):
            raise ValueError(f"case missing {field}")
    if not isinstance(case.get("claims"), list) or not case["claims"]:
        raise ValueError("case has no empirical claims")

    refs = {
        "source_repo": "Spectating101/nocturnal-oversight",
        "frozen_empirical_commit": identity["frozen_commit"],
        "freeze_manifest_commit": identity.get("freeze_manifest_commit"),
        "frozen_case_path": identity["case_path"],
        "frozen_case_sha256": identity["case_sha256"],
        "candidate_id": cid,
        "matter_id": case["matter_id"],
        "chain_id": case["chain_id"],
        "country": "China",
        "domain": case["domain"],
        "cohort": "development",
        "paper_scope": freeze["paper_scope"],
        "national_validation_approved": False,
        "cross_country_comparison_ready": False,
    }
    # Namespace all external keys by the frozen matter ID: repeated text or
    # event ordinal across cases must never merge independent investigations.
    cluster_key = f"nocturnal-{cid}"
    anchor_key = f"nocturnal-{cid}-scope"
    nodes: list[dict[str, Any]] = [{
        "key": anchor_key, "statement": f"Nocturnal investigation scope: {_text(case['title'])}",
        "layer": "neutral", "kind": "concept",
        "clusters": [cluster_key], "tags": ["source_case_context"],
        "provenance": {**refs, "boundary": "case context, not a validated causal conclusion"},
    }]
    edges: list[dict[str, Any]] = []
    seen_events: dict[str, tuple[str, list[str]]] = {}
    skipped_claims = 0
    skipped_edges = 0
    for index, item in enumerate(case["claims"]):
        if not isinstance(item, dict):
            raise ValueError("claim record must be object")
        # Older frozen development cases sometimes omit review_state entirely.
        # Missing is NOT accepted. Preserve accepted evidence without upgrading it.
        review = _text(item.get("editorial_review_state") or "unreviewed").lower()
        if review not in _REVIEW:
            raise ValueError(f"invalid editorial review state in claim {index}")
        if review != "accepted":
            skipped_claims += 1
            continue
        if item.get("matter_id") != case["matter_id"]:
            raise ValueError("claim matter ID does not match frozen case")
        event = _text(item.get("event_id"))
        if not event or event in seen_events:
            raise ValueError("accepted event IDs must be unique and nonempty")
        statement = _text(item.get("claim"))
        if not statement:
            raise ValueError("accepted claim text must not be empty")
        sources = _source_urls(item.get("sources"))
        if not sources:
            raise ValueError("accepted claim lacks original source citations")
        roles = item.get("event_actor_roles") or []
        if not isinstance(roles, list):
            raise ValueError("event actor roles must be a list")
        media = item.get("media_provenance") or []
        if not isinstance(media, list):
            raise ValueError("media provenance must be a list")
        node_key = f"nocturnal-{cid}-event-{index}"
        seen_events[event] = (node_key, sources)
        provenance = {
            **refs,
            "event_id": event,
            "observed_at": item.get("observed_at"),
            "status_stage": item.get("status_stage"),
            "editorial_review_state": review,
            "entity_ids": list(item.get("entity_ids") or []),
            "event_actor_roles": roles,
            "media_provenance": media,
            "boundary": "accepted Nocturnal case record; not independent truth/causality verification",
        }
        nodes.append({
            "key": node_key, "statement": statement,
            "layer": "practical", "kind": "observation",
            "clusters": [cluster_key],
            "tags": [f"status_stage:{_text(item.get('status_stage'))}"],
            "source_refs": sources,
            "provenance": provenance,
        })
        edges.append({
            "source": node_key, "target": anchor_key,
            "relation": "CONTEXT_FOR", "status": "qualified",
            "evidence_refs": sources,
            "provenance": {
                **refs, "event_id": event,
                "boundary": "belongs to source matter, not SUPPORTS or CAUSES",
            },
        })
    if not seen_events:
        raise ValueError("no accepted, source-backed events to import")

    seen_trace: set[tuple[str, str, str]] = set()
    for item in case["claims"]:
        if item.get("editorial_review_state") != "accepted":
            continue
        for trace in item.get("trace_edges") or []:
            if not isinstance(trace, dict):
                raise ValueError("trace edge must be object")
            review = _text(trace.get("review_state") or "needs_review").lower()
            if review not in _REVIEW:
                raise ValueError("invalid trace-edge review state")
            if review != "accepted":
                skipped_edges += 1
                continue
            rel = _text(trace.get("relation_type")).lower()
            epistemic = _text(trace.get("epistemic_state") or "attributed").lower()
            if rel not in _RELATIONS or epistemic not in _EPISTEMIC:
                raise ValueError("invalid accepted TRACE relation or epistemic state")
            src = _text(trace.get("source_event_id"))
            dst = _text(trace.get("target_event_id"))
            if src not in seen_events or dst not in seen_events or src == dst:
                raise ValueError("accepted TRACE link refers to absent/unreviewed event or itself")
            identity_key = (src, dst, rel)
            if identity_key in seen_trace:
                continue
            seen_trace.add(identity_key)
            src_key, src_urls = seen_events[src]
            dst_key, dst_urls = seen_events[dst]
            evidences = _source_urls(trace.get("evidence_urls") or list(dict.fromkeys(src_urls + dst_urls)))
            if not evidences:
                raise ValueError("accepted TRACE edge must be source-backed")
            edges.append({
                "source": src_key, "target": dst_key,
                "relation": "NOCTURNAL_" + rel.upper(),
                # Qualified means the relationship is reviewed *in the source*
                # without asserting causal status at the Cite-Refinery layer.
                "status": "qualified", "evidence_refs": evidences,
                "provenance": {
                    **refs, "nocturnal_relation_type": rel,
                    "source_event_id": src, "target_event_id": dst,
                    "review_state": review, "epistemic_state": epistemic,
                    "rationale": trace.get("rationale"),
                    "boundary": "source-reviewed accountability link, not independent causal proof",
                },
            })
    return {
        "schema": SEMANTIC_PACKET_SCHEMA,
        "source_system": "nocturnal",
        "clusters": [{
            "key": cluster_key,
            "title": _text(case["title"]),
            "tags": [str(case["domain"]), "frozen_development_case"],
            "provenance": refs,
        }],
        "nodes": nodes,
        "edges": edges,
        "conversion_metadata": {
            **refs,
            "source_claims_total": len(case["claims"]),
            "accepted_events_imported": len(seen_events),
            "unaccepted_claims_omitted": skipped_claims,
            "reviewed_trace_edges_imported": len(seen_trace),
            "unaccepted_trace_edges_omitted": skipped_edges,
            "boundary": (
                "Frozen development case only; not a China-national prevalence sample, "
                "cross-country comparison, proof of causation, or Cite/Refinery evidence."
            ),
        },
    }
