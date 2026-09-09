"""Strict intake-review contract; draft validity never means completed review.

This module intentionally has no domain-state mutation or network access.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

SCHEMA = 'problem-owner-intake-review/v0.1'
DISPOSITIONS = ('confirm', 'reframe', 'stale', 'already-resolved', 'decline', 'undecided')
LIST_FIELDS = (
    'factual_corrections', 'missing_constraints', 'acceptable_work_subproblem_ids',
    'unacceptable_work_subproblem_ids', 'access_or_safeguarding_corrections',
    'funding_or_resource_notes',
)
TEXT_FIELDS = ('desired_outcome_or_priority', 'owner_notes')
BOOL_FIELDS = ('source_still_current', 'owner_identity_and_role_correct')
RESPONSE_FIELDS = set(LIST_FIELDS + TEXT_FIELDS + BOOL_FIELDS) | {
    'item_scores', 'reframe_required', 'disposition',
}
PACK_FIELDS = {'schema', 'intake_id', 'problem_id', 'potential_owner', 'source_ref',
               'instructions', 'problem', 'rubric', 'response', 'allowed_dispositions', 'privacy_note'}


def _strings(value: Any, *, nonempty: bool = False) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and (not nonempty or bool(item.strip())) for item in value
    )


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode('utf-8')).hexdigest()


def review_context(pack: dict[str, Any]) -> dict[str, Any]:
    """Everything except response is issued by the curator, not editable by the reviewer."""
    return {key: value for key, value in pack.items() if key != 'response'}


def validate_owner_review_response(
    pack: Any, *, require_complete: bool = False, expected_pack: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(pack, dict) or pack.get('schema') != SCHEMA:
        return ['unsupported owner-review schema']
    extra = set(pack) - PACK_FIELDS
    if extra:
        errors.append('unknown review fields: ' + ', '.join(sorted(extra)))
    for key in ('intake_id', 'problem_id', 'potential_owner'):
        if not isinstance(pack.get(key), str) or not pack[key].strip():
            errors.append(f'{key} is required')
    intake_id = pack.get('intake_id')
    problem_id = pack.get('problem_id')
    if not isinstance(intake_id, str) or not intake_id.startswith('intake:') or not intake_id[7:].strip():
        errors.append('intake_id must have a non-empty intake: suffix')
    elif problem_id != 'problem:' + intake_id[7:]:
        errors.append('problem_id does not align to intake_id')
    if pack.get('allowed_dispositions') != list(DISPOSITIONS):
        errors.append('allowed_dispositions must match the fixed review contract')
    if not _strings(pack.get('instructions'), nonempty=True) or not pack.get('instructions'):
        errors.append('instructions must contain non-empty strings')
    for key in ('source_ref', 'privacy_note'):
        if key in pack and not isinstance(pack[key], str):
            errors.append(f'{key} must be a string')
    problem, rubric, response = (pack.get(key) for key in ('problem', 'rubric', 'response'))
    for name, value in (('problem', problem), ('rubric', rubric), ('response', response)):
        if not isinstance(value, dict):
            errors.append(f'{name} object is required')
    if not all(isinstance(value, dict) for value in (problem, rubric, response)):
        return errors
    for key in ('title', 'observed_condition', 'unresolved_core', 'authority_boundary'):
        if not isinstance(problem.get(key), str) or not problem[key].strip():
            errors.append(f'problem.{key} is required')
    for key in ('uncertainties', 'constraints', 'available_resources_reported', 'requested_support_reported'):
        if not _strings(problem.get(key)):
            errors.append(f'problem.{key} must be a list of strings')
    items = rubric.get('items')
    if rubric.get('name') != 'owner_agreement' or not _strings(items, nonempty=True) or not items:
        errors.append('a non-empty owner_agreement rubric is required')
    work = problem.get('candidate_work')
    known_ids: set[str] = set()
    if not isinstance(work, list):
        errors.append('candidate_work must be a list')
    else:
        for row in work:
            if not isinstance(row, dict):
                errors.append('each candidate work entry must be an object')
                continue
            key = row.get('subproblem_id')
            if not isinstance(key, str) or not key.strip():
                errors.append('candidate work subproblem_id is required')
            elif key in known_ids:
                errors.append('duplicate candidate work subproblem_id')
            else:
                known_ids.add(key)
            for field in ('title', 'description', 'kind', 'status', 'effort'):
                if not isinstance(row.get(field), str):
                    errors.append(f'candidate work {field} must be a string')
            for field in ('expected_outputs', 'required_credentials'):
                if not _strings(row.get(field)):
                    errors.append(f'candidate work {field} must be a list of strings')
    if set(response) != RESPONSE_FIELDS:
        errors.append('response must contain exactly the defined review fields')
    disposition = response.get('disposition')
    if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
        errors.append('response disposition is invalid')
    complete = isinstance(disposition, str) and disposition in DISPOSITIONS[:-1]
    if require_complete and not complete:
        errors.append('a completed disposition is required; an undecided draft is not a returned review')
    scores = response.get('item_scores')
    if not isinstance(scores, list) or not isinstance(items, list) or len(scores) != len(items):
        errors.append('item_scores must align to owner_agreement rubric items')
    elif any(not (type(score) is int and score in (0, 1)) and not (score is None and not complete) for score in scores):
        errors.append('item_scores must be binary integers; null is permitted only for an undecided draft')
    for key in BOOL_FIELDS:
        value = response.get(key)
        if type(value) is not bool and not (value is None and not complete):
            errors.append(f'{key} must be a boolean for a completed owner review')
    if type(response.get('reframe_required')) is not bool:
        errors.append('reframe_required must be a boolean')
    for key in LIST_FIELDS:
        if not _strings(response.get(key), nonempty=True):
            errors.append(f'{key} must be a list of non-empty strings')
    for key in TEXT_FIELDS:
        if not isinstance(response.get(key), str):
            errors.append(f'{key} must be a string')
    choice_sets: list[set[str]] = []
    for key in ('acceptable_work_subproblem_ids', 'unacceptable_work_subproblem_ids'):
        values = response.get(key)
        if _strings(values):
            selected = set(values)
            if len(selected) != len(values):
                errors.append(f'{key} contains duplicates')
            if selected - known_ids:
                errors.append(f'{key} contains unknown subproblem IDs')
            choice_sets.append(selected)
    if len(choice_sets) == 2 and choice_sets[0] & choice_sets[1]:
        errors.append('work cannot be both acceptable and unacceptable')
    if disposition == 'confirm':
        if response.get('source_still_current') is not True or response.get('owner_identity_and_role_correct') is not True:
            errors.append('confirm requires current need and correct owner identity/role')
        if response.get('reframe_required') is not False:
            errors.append('confirm conflicts with reframe_required')
    if disposition == 'reframe' and response.get('reframe_required') is not True:
        errors.append('reframe disposition requires reframe_required=true')
    if disposition == 'stale' and response.get('source_still_current') is not False:
        errors.append('stale disposition requires source_still_current=false')
    if disposition == 'reframe' and not any(response.get(key) for key in LIST_FIELDS[:2] + ('access_or_safeguarding_corrections',) + TEXT_FIELDS):
        errors.append('reframe requires corrections, constraints, or explanatory notes')
    if expected_pack is not None:
        expected_errors = validate_owner_review_response(expected_pack)
        if expected_errors:
            errors.append('issued original review pack is invalid')
        else:
            try:
                if digest(review_context(pack)) != digest(review_context(expected_pack)):
                    errors.append('returned review context differs from the issued original; only response may change')
            except (TypeError, ValueError):
                errors.append('review contains non-JSON or non-finite values')
    return errors


def build_owner_review_receipt(
    original: dict[str, Any], returned: dict[str, Any], *, actor: str, receipt_ref: str,
) -> dict[str, Any]:
    """Record a validated return for curator attention, never authenticate or apply it.

    The original must be the curator-retained issued pack, not a second file
    supplied by the respondent. Hash binding provides consistency, not identity.
    """
    errors = validate_owner_review_response(returned, require_complete=True, expected_pack=original)
    for key, value in (('actor', actor), ('receipt_ref', receipt_ref)):
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{key} is required')
    if errors:
        raise ValueError('; '.join(errors))
    returned_hash = digest(returned)
    response = deepcopy(returned['response'])
    next_action = {
        'confirm': 'Verify respondent role, then curate the accepted work; no work is opened automatically.',
        'reframe': 'Revise the formulation using the corrections, then issue a fresh review.',
        'stale': 'Recheck the source or retire the candidate; do not recruit against a stale need.',
        'already-resolved': 'Verify the resolution and consider retiring the candidate, preserving its history.',
        'decline': 'Do not advance this owner-dependent work; review the decline with the curator.',
    }[response['disposition']]
    return {
        'schema': 'problem-owner-review-return/v0.1',
        'id': 'owner-return:' + returned_hash[:20],
        'intake_id': original['intake_id'], 'problem_id': original['problem_id'],
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'recorded_by': actor.strip(), 'receipt_ref': receipt_ref.strip(),
        'issued_context_sha256': digest(review_context(original)),
        'returned_pack_sha256': returned_hash,
        'status': 'pending-curator-decision', 'response': response,
        'next_action': next_action,
        'respondent_identity_verified': False,
        'owner_confirmation_applied': False, 'work_opened': False,
        'funding_committed': False, 'authority_granted': False,
        'privacy': 'Private curator receipt. Do not publish raw owner corrections or personal information.',
        'claim_boundary': 'File validation is not respondent authentication, owner endorsement, publication, funding, or permission to act.',
    }
