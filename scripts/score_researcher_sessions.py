"""Score independently coded Cite-Refinery research navigation sessions.

No access to private case DB or web is required. This instrument evaluates
submitted structured answers, not participant intent, source validity or UX.
Free-text interpretations require blind human review outside this script.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "cite_refinery.researcher_session.v1"
TASKS = {
    "dog_national_survey": {
        "correct_choice": "decline_not_significant",
        "required_keys": {"tw_periodic_estimate", "survey_decline_not_significant"},
        "required_domains": {"animal.moa.gov.tw"},
    },
    "dog_talea_capability": {
        "correct_choice": "not_demonstrated",
        "required_keys": {"talea", "talea_sighting_photo_limit", "identity_reconciliation_requirement"},
        "required_domains": {"icam-coalition.org"},
    },
    "dog_shoushan_scope": {
        "correct_choice": "local_model_not_national_proof",
        "required_keys": {"shoushan_immigration"},
        "required_domains": {"sciencedirect.com"},
    },
    "dog_policy_outcome": {
        "correct_choice": "policy_intent_not_verified_effect",
        "required_keys": {"tw_source_control_policy", "longitudinal_feedback_requirement"},
        "required_domains": {"animal.moa.gov.tw"},
    },
}
ALLOWED_CHOICES = {
    "dog_national_survey": {"decline_significant", "decline_not_significant", "cannot_determine"},
    "dog_talea_capability": {"complete_photo_estimator", "not_demonstrated", "cannot_determine"},
    "dog_shoushan_scope": {"national_proof", "local_model_not_national_proof", "cannot_determine"},
    "dog_policy_outcome": {"verified_effect", "policy_intent_not_verified_effect", "cannot_determine"},
}


def score_session(record: dict) -> dict:
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise ValueError("invalid session schema")
    if record.get("case") != "taiwan-free-roaming-dogs-survey-management":
        raise ValueError("incorrect case identity")
    if record.get("mode") not in {"independent", "assisted", "automated"}:
        raise ValueError("mode must be independent, assisted or automated")
    if not isinstance(record.get("session_id"), str) or not record["session_id"].strip():
        raise ValueError("nonempty pseudonymous session_id required")
    tasks = record.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != len(TASKS):
        raise ValueError("exactly four task responses required")
    seen = set()
    results = []
    for item in tasks:
        if not isinstance(item, dict):
            raise ValueError("task responses must be objects")
        key = item.get("task_id")
        if key not in TASKS or key in seen:
            raise ValueError("unknown or duplicated task_id")
        seen.add(key)
        if item.get("choice") not in ALLOWED_CHOICES[key]:
            raise ValueError("invalid coded answer for " + key)
        evidence = item.get("evidence_node_keys")
        domains = item.get("source_domains")
        seconds = item.get("elapsed_seconds")
        if not isinstance(evidence, list) or any(not isinstance(v, str) for v in evidence):
            raise ValueError("evidence_node_keys must be string list")
        if not isinstance(domains, list) or any(not isinstance(v, str) for v in domains):
            raise ValueError("source_domains must be string list")
        if type(seconds) not in (int, float) or not 0 <= seconds <= 7200:
            raise ValueError("elapsed_seconds must be between 0 and 7200")
        if not isinstance(item.get("used_hint"), bool):
            raise ValueError("used_hint must be boolean")
        rubric = TASKS[key]
        choice_correct = item["choice"] == rubric["correct_choice"]
        evidence_complete = rubric["required_keys"].issubset(set(evidence))
        source_complete = rubric["required_domains"].issubset(set(domains))
        # A correct forced-choice response is not equated with source-grounded success.
        independent = record["mode"] == "independent" and not item["used_hint"]
        results.append({
            "task_id": key,
            "choice_correct": choice_correct,
            "evidence_complete": evidence_complete,
            "source_complete": source_complete,
            "unassisted": independent,
            "source_grounded_success": bool(choice_correct and evidence_complete and source_complete and independent),
            "elapsed_seconds": seconds,
        })
    return {
        "schema": "cite_refinery.researcher_session_score.v1",
        "session_id": record["session_id"],
        "case": record["case"],
        "mode": record["mode"],
        "task_count": len(results),
        "correct_choices": sum(x["choice_correct"] for x in results),
        "evidence_complete_tasks": sum(x["evidence_complete"] for x in results),
        "source_grounded_unassisted_tasks": sum(x["source_grounded_success"] for x in results),
        "total_elapsed_seconds": sum(x["elapsed_seconds"] for x in results),
        "results": results,
        "limitations": [
            "Self-reported answers and timings are not independently verified.",
            "Source domain and node key selections are not proof of source comprehension.",
            "No human participants, usability study, or independently validated outcomes are implied by this score.",
            "Human reviewers must separately evaluate explanations and unexpected interpretations.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = score_session(json.loads(args.session_json.read_text(encoding="utf-8")))
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
