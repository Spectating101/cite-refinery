from __future__ import annotations

from typing import Any, Mapping


REQUEST_SCHEMA = "cite_refinery.nocturnal_feedback_request.v1"
RESULT_SCHEMA = "nocturnal.cite_refinery_feedback_result.v1"
_ALLOWED_RELATIONS = {
    "post_intervention_observation",
    "implementation_event",
    "adverse_event",
    "adoption_signal",
    "outcome_signal",
}
_ALLOWED_DIRECTIONS = {"improved", "worsened", "no_change", "mixed", "unknown"}


def validate_feedback_result(packet: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a Nocturnal follow-up result against one stored request.

    The contract is deliberately observational. Nocturnal may report what happened
    after an intervention, but v1 never upgrades temporal follow-up into causal proof.
    """

    if str(packet.get("schema") or "") != RESULT_SCHEMA:
        raise ValueError(f"feedback result schema must be {RESULT_SCHEMA}")
    for key in ("request_id", "project_id", "experiment_id"):
        if str(packet.get(key) or "") != str(request.get(key) or ""):
            raise ValueError(f"feedback result {key} does not match request")

    expected_runs = sorted(str(value) for value in request.get("run_ids", []) if str(value))
    actual_runs = sorted(str(value) for value in packet.get("run_ids", []) if str(value))
    if actual_runs != expected_runs:
        raise ValueError("feedback result run_ids do not match request")

    raw_observations = packet.get("observations")
    if not isinstance(raw_observations, list) or not raw_observations:
        raise ValueError("feedback result requires at least one observation")
    if len(raw_observations) > 1000:
        raise ValueError("feedback result may contain at most 1000 observations")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in raw_observations:
        if not isinstance(raw, Mapping):
            raise ValueError("feedback observations must be objects")
        observation_id = str(raw.get("observation_id") or "").strip()
        text = str(raw.get("text") or "").strip()
        if not observation_id or not text:
            raise ValueError("feedback observation requires observation_id and text")
        if observation_id in seen_ids:
            raise ValueError(f"duplicate feedback observation_id: {observation_id}")
        seen_ids.add(observation_id)

        relation = str(raw.get("relation_to_intervention") or "post_intervention_observation").strip()
        if relation not in _ALLOWED_RELATIONS:
            raise ValueError(f"unsupported relation_to_intervention: {relation}")
        direction = str(raw.get("outcome_direction") or "unknown").strip()
        if direction not in _ALLOWED_DIRECTIONS:
            raise ValueError(f"unsupported outcome_direction: {direction}")
        causal_status = str(raw.get("causal_status") or "not_established").strip()
        if causal_status != "not_established":
            raise ValueError("feedback v1 requires causal_status=not_established")

        sources = raw.get("sources") or []
        if not isinstance(sources, list):
            raise ValueError("feedback observation sources must be a list")
        normalized.append(
            {
                "observation_id": observation_id,
                "matter_id": str(raw.get("matter_id") or "").strip() or None,
                "event_id": str(raw.get("event_id") or "").strip() or None,
                "text": text,
                "observed_at": str(raw.get("observed_at") or "").strip() or None,
                "status_stage": str(raw.get("status_stage") or "").strip() or None,
                "sources": [str(value).strip() for value in sources if str(value).strip()],
                "relation_to_intervention": relation,
                "outcome_direction": direction,
                "causal_status": causal_status,
                "provenance": dict(raw.get("provenance") or {}),
            }
        )

    collection = packet.get("collection") or {}
    if collection and not isinstance(collection, Mapping):
        raise ValueError("feedback result collection must be an object")
    return {
        "schema": RESULT_SCHEMA,
        "request_id": str(request["request_id"]),
        "project_id": str(request["project_id"]),
        "experiment_id": str(request["experiment_id"]),
        "run_ids": expected_runs,
        "observations": normalized,
        "collection": dict(collection),
        "boundary": (
            "These are post-intervention empirical observations. Temporal order, reported effects, or outcome direction "
            "do not by themselves establish that the intervention caused the observed change."
        ),
    }
