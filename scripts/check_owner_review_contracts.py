"""Cross-language parity and real JSON Schema checks for the frozen review contract."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from cite_refinery.problem_intake import OwnerIntake
from cite_refinery.intake_review import build_intake_owner_review_pack, validate_owner_review_response

intake = OwnerIntake.load(ROOT / 'pilot/intake/yzu-yongfeng-after-school.v0.1.json')
draft = build_intake_owner_review_pack(intake, intake.to_problem_packet(steward='test'),
    rubrics=json.loads((ROOT / 'pilot/rubrics.v0.1.json').read_text()))
complete = deepcopy(draft)
complete['response'].update(disposition='confirm', source_still_current=True,
    owner_identity_and_role_correct=True, item_scores=[1] * len(draft['rubric']['items']))
cases = [{'name': 'draft', 'pack': draft, 'valid': True}, {'name': 'complete', 'pack': complete, 'valid': True}]
for value in (None, True, '1', 2, -1, 0.5, {}):
    bad = deepcopy(complete); bad['response']['item_scores'][0] = value
    cases.append({'name': f'bad-score-{value}', 'pack': bad, 'valid': False})
for field in ('source_still_current', 'owner_identity_and_role_correct', 'reframe_required'):
    bad = deepcopy(complete); bad['response'][field] = 'false'
    cases.append({'name': field, 'pack': bad, 'valid': False})
for field, value in [('authority_granted', True), ('application_submitted', True)]:
    bad = deepcopy(complete); bad['response'][field] = value
    cases.append({'name': field, 'pack': bad, 'valid': False})
for variant in ('unknown-work', 'overlap', 'duplicate', 'empty-rubric', 'changed-dispositions', 'stale-confirm', 'identity', 'missing-field'):
    bad = deepcopy(complete); work_id = bad['problem']['candidate_work'][0]['subproblem_id']
    if variant == 'unknown-work': bad['response']['acceptable_work_subproblem_ids'] = ['psub:unknown']
    if variant == 'overlap':
        bad['response']['acceptable_work_subproblem_ids'] = [work_id]
        bad['response']['unacceptable_work_subproblem_ids'] = [work_id]
    if variant == 'duplicate': bad['response']['acceptable_work_subproblem_ids'] = [work_id, work_id]
    if variant == 'empty-rubric': bad['rubric']['items'] = []; bad['response']['item_scores'] = []
    if variant == 'changed-dispositions': bad['allowed_dispositions'].append('funded'); bad['response']['disposition'] = 'funded'
    if variant == 'stale-confirm': bad['response']['source_still_current'] = False
    if variant == 'identity': bad['problem_id'] = 'problem:other'
    if variant == 'missing-field': del bad['response']['funding_or_resource_notes']
    cases.append({'name': variant, 'pack': bad, 'valid': False})
js = "require(process.argv[1]); let s=''; process.stdin.on('data',d=>s+=d); process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(s).map(p=>OwnerReviewContract.errors(p).length===0))));"
run = subprocess.run(['node', '-e', js, str(ROOT / 'prototype/owner-review-contract.js')],
    input=json.dumps([case['pack'] for case in cases]), text=True, capture_output=True, check=True)
js_values = json.loads(run.stdout)
for case, browser_valid in zip(cases, js_values):
    python_valid = not validate_owner_review_response(case['pack'])
    assert python_valid == browser_valid == case['valid'], (case['name'], python_valid, browser_valid)
schema = json.loads((ROOT / 'schemas/problem-owner-intake-review.v0.1.schema.json').read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
validator.validate(draft); validator.validate(complete)
for name in ('empty-rubric', 'changed-dispositions', 'missing-field', 'stale-confirm'):
    bad = next(c['pack'] for c in cases if c['name'] == name)
    assert list(validator.iter_errors(bad)), name
print(json.dumps({'cross_language_cases': len(cases), 'parity': 'passed', 'schema_validation': 'passed'}))
