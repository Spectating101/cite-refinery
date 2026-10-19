# Acceptance milestone 03 — independent researcher task evaluation (instrument)

**Status: instrument implemented; participant testing NOT performed.**

This is a proposed reproducible test of the value of the *research navigation experience*, not a third topic acceptance case. It operates against the existing source-reviewed dog case 02. Existing v0.24 infrastructure and case 01 / 02 fixtures are not modified.

## Question

Can an unfamiliar researcher, without operator instructions, distinguish sourced statements from unsupported inferences and locate the supporting evidence for each of the four case-02 questions?

## Procedure

1. Recruit readers who did not build Cite-Refinery. Obtain consent; allow withdrawal. Avoid collecting names, IPs, contact details or identifiable recordings in exported research records.
2. Give the evaluator access to the same authorized isolated dog acceptance workspace and only the four questions in `docs/PRODUCT_ACCEPTANCE_FREE_ROAMING_DOGS_02.md`. Do not give them the answer key, code, node IDs or navigation hints.
3. Ask them to navigate the map, choose the answer that best matches the evidence, cite specific inspected node keys and source domains, and explain in their own words why the evidence does *not* establish stronger claims. Record elapsed time per question and any assistance.
4. Record a pseudonymous session ID; mark `mode=independent` only if the study was a real independent navigation attempt. Record `used_hint=true` per assisted task. Preserve actual failures, withdrawals and incomplete sessions separately; **do not fabricate complete answers**.
5. A reviewer blinded to the score should read the written explanations, note whether the researcher correctly explains the national significance caveat, Talea scope, Shoushan applicability and policy-evaluation uncertainty, and record misunderstandings. Disagreements go to a second independent adjudicator.
6. Run the deterministic scorer on coded complete sessions, then report both successes **and failures**, study size, recruitment conditions, median time, assistance rate and reviewer disagreements. Do not present a synthetic fixture as a study result.

## Coding contract

The scorer, `scripts/score_researcher_sessions.py`, expects a JSON object:

```json
{
  "schema": "cite_refinery.researcher_session.v1",
  "case": "taiwan-free-roaming-dogs-survey-management",
  "session_id": "pseudonymous-id",
  "mode": "independent",
  "tasks": [
    {
      "task_id": "dog_national_survey",
      "choice": "decline_not_significant",
      "evidence_node_keys": ["tw_periodic_estimate", "survey_decline_not_significant"],
      "source_domains": ["animal.moa.gov.tw"],
      "elapsed_seconds": 75,
      "used_hint": false
    },
    {
      "task_id": "dog_talea_capability",
      "choice": "not_demonstrated",
      "evidence_node_keys": ["talea", "talea_sighting_photo_limit", "identity_reconciliation_requirement"],
      "source_domains": ["icam-coalition.org"],
      "elapsed_seconds": 90,
      "used_hint": false
    },
    {
      "task_id": "dog_shoushan_scope",
      "choice": "local_model_not_national_proof",
      "evidence_node_keys": ["shoushan_immigration"],
      "source_domains": ["sciencedirect.com"],
      "elapsed_seconds": 80,
      "used_hint": false
    },
    {
      "task_id": "dog_policy_outcome",
      "choice": "policy_intent_not_verified_effect",
      "evidence_node_keys": ["tw_source_control_policy", "longitudinal_feedback_requirement"],
      "source_domains": ["animal.moa.gov.tw"],
      "elapsed_seconds": 70,
      "used_hint": false
    }
  ]
}
```

**The above values are an illustrative coding example, not participant evidence.** Do not submit or publish it as empirical data.

Run `PYTHONPATH=src:. python3 scripts/score_researcher_sessions.py path/to/session.json --output path/to/score.json`.

The instrument requires the four unique tasks and checks correct answer category, required evidence nodes, source domain, and absence of help. Only if all conditions are satisfied is a task counted as `source_grounded_success`. `automated` and `assisted` sessions can be scored diagnostically but are not counted as unassisted researcher successes.

## Locked expected answers and counterclaims

| Task ID | Correct answer category | Wrong inference to catch |
| --- | --- | --- |
| `dog_national_survey` | `decline_not_significant` | National point estimate decrease proves statistical significance |
| `dog_talea_capability` | `not_demonstrated` | Talea offers photo identification and validated population estimation |
| `dog_shoushan_scope` | `local_model_not_national_proof` | Shoushan modeling proves nationwide causal effectiveness |
| `dog_policy_outcome` | `policy_intent_not_verified_effect` | A published policy announcement measures its own success |

The answers are tied to the **reviewed, dated sources** of case 02. Future changed sources require explicit re-review, not silently changing expected classifications.

## Decision gate

Provisional usability target for a small exploratory study: **at least five unrelated researchers**, each attempting all four questions; **at least 80% of attempted questions** source-grounded and unassisted, **zero uncorrected false causal/effectiveness claims** in human-reviewed explanations. This is a product target, not a statistical validation threshold or a result.

If performance falls short, report the failure and diagnose navigation, source visibility, conceptual confusion, and time-to-evidence before adding graph capacity. If it meets target, the next gate remains *independent Program-side execution and methodology review*, not a claim of field-tested dog management.

## Limits and safeguards

- Structured node/source choices can be copied or guessed; reviewer explanation and observed study conduct are essential.
- Scores do not establish research quality, independent fact replication, interface accessibility or actual intervention efficacy.
- Human tasks are not validated by CI or Chrome automation; human findings must be collected separately.
- Keep raw participant data private, minimize retention and publish only appropriately aggregated results.
- Correct choices and the illustrative example are accessible in this repository: evaluators should not allow participants to consult them during trials.
