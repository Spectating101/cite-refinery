/* Intake-review validation is mirrored at the Python ingestion boundary.
   Browser validation improves feedback; it does not grant trust or authority. */
(() => {
  const schema = 'problem-owner-intake-review/v0.1';
  const dispositions = ['confirm', 'reframe', 'stale', 'already-resolved', 'decline', 'undecided'];
  const lists = ['factual_corrections', 'missing_constraints', 'acceptable_work_subproblem_ids',
    'unacceptable_work_subproblem_ids', 'access_or_safeguarding_corrections', 'funding_or_resource_notes'];
  const texts = ['desired_outcome_or_priority', 'owner_notes'];
  const bools = ['source_still_current', 'owner_identity_and_role_correct'];
  const responseFields = [...lists, ...texts, ...bools, 'item_scores', 'reframe_required', 'disposition'].sort();
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const strings = (value, nonempty = false) => Array.isArray(value) && value.every(item =>
    typeof item === 'string' && (!nonempty || item.trim().length > 0));
  function errors(pack, requireComplete = false) {
    const out = [];
    if (!object(pack) || pack.schema !== schema) return ['Unsupported owner-review schema.'];
    const packFields = ['schema','intake_id','problem_id','potential_owner','source_ref','instructions','problem','rubric','response','allowed_dispositions','privacy_note'];
    if (Object.keys(pack).some(key => !packFields.includes(key))) out.push('Unknown review fields.');
    ['source_ref', 'privacy_note'].forEach(key => { if (key in pack && typeof pack[key] !== 'string') out.push(`Invalid ${key}.`); });
    if (typeof pack.intake_id !== 'string' || !pack.intake_id.startsWith('intake:') || !pack.intake_id.slice(7).trim() ||
        pack.problem_id !== 'problem:' + pack.intake_id.slice(7)) out.push('Problem and intake identity do not match.');
    if (typeof pack.potential_owner !== 'string' || !pack.potential_owner.trim()) out.push('Potential owner is missing.');
    if (JSON.stringify(pack.allowed_dispositions) !== JSON.stringify(dispositions)) out.push('Review decision choices have been changed.');
    if (!strings(pack.instructions, true) || !pack.instructions.length) out.push('Review instructions are missing.');
    if (!object(pack.problem) || !object(pack.rubric) || !object(pack.response)) return [...out, 'Problem, rubric and response objects are required.'];
    const p = pack.problem, r = pack.response, items = pack.rubric.items;
    ['title', 'observed_condition', 'unresolved_core', 'authority_boundary'].forEach(key => {
      if (typeof p[key] !== 'string' || !p[key].trim()) out.push(`Problem ${key} is missing.`);
    });
    ['uncertainties', 'constraints', 'available_resources_reported', 'requested_support_reported'].forEach(key => {
      if (!strings(p[key])) out.push(`Problem ${key} must be a list of text.`);
    });
    if (pack.rubric.name !== 'owner_agreement' || !strings(items, true) || !items.length) out.push('The review rubric is empty or invalid.');
    const known = new Set();
    if (!Array.isArray(p.candidate_work)) out.push('Candidate work must be a list.');
    else p.candidate_work.forEach(work => {
      if (!object(work)) { out.push('Invalid candidate work item.'); return; }
      if (typeof work.subproblem_id !== 'string' || !work.subproblem_id.trim() || known.has(work.subproblem_id)) out.push('Work identifiers must be present and unique.');
      known.add(work.subproblem_id);
      ['title', 'description', 'kind', 'status', 'effort'].forEach(key => { if (typeof work[key] !== 'string') out.push(`Invalid work ${key}.`); });
      ['expected_outputs', 'required_credentials'].forEach(key => { if (!strings(work[key])) out.push(`Invalid work ${key}.`); });
    });
    if (JSON.stringify(Object.keys(r).sort()) !== JSON.stringify(responseFields)) out.push('Response fields do not match the review contract.');
    if (!dispositions.includes(r.disposition)) out.push('Choose a valid review decision.');
    const complete = dispositions.slice(0, -1).includes(r.disposition);
    if (requireComplete && !complete) out.push('Choose a final decision before preparing a completed response.');
    if (!Array.isArray(r.item_scores) || !Array.isArray(items) || r.item_scores.length !== items.length) out.push('Scores do not match the rubric.');
    else r.item_scores.forEach((score, i) => {
      if (score !== 0 && score !== 1 && !(score === null && !complete)) out.push(`Answer review item ${i + 1}.`);
    });
    bools.forEach(key => { if (typeof r[key] !== 'boolean' && !(r[key] === null && !complete)) out.push(`Answer ${key === 'source_still_current' ? 'whether the need is current' : 'whether the owner and role are correct'}.`); });
    if (typeof r.reframe_required !== 'boolean') out.push('Reframe requirement must be a boolean.');
    lists.forEach(key => { if (!strings(r[key], true)) out.push(`${key} must be a list of non-empty text.`); });
    texts.forEach(key => { if (typeof r[key] !== 'string') out.push(`${key} must be text.`); });
    const choices = ['acceptable_work_subproblem_ids', 'unacceptable_work_subproblem_ids'];
    choices.forEach(key => {
      if (strings(r[key])) {
        if (new Set(r[key]).size !== r[key].length) out.push('Duplicate work decisions are not allowed.');
        if (r[key].some(id => !known.has(id))) out.push('A work decision refers to a different problem.');
      }
    });
    if (strings(r[choices[0]]) && strings(r[choices[1]]) && r[choices[0]].some(id => r[choices[1]].includes(id))) out.push('Work cannot be both acceptable and unacceptable.');
    if (r.disposition === 'confirm' && (r.source_still_current !== true || r.owner_identity_and_role_correct !== true || r.reframe_required !== false)) out.push('Confirmation requires a current need, a correct owner/role and no material reframing.');
    if (r.disposition === 'reframe' && r.reframe_required !== true) out.push('Select the material-reframing checkbox for a reframe decision.');
    if (r.disposition === 'stale' && r.source_still_current !== false) out.push('A stale decision requires the current-need answer to be No.');
    if (r.disposition === 'reframe' && !['factual_corrections', 'missing_constraints', 'access_or_safeguarding_corrections', ...texts].some(key => r[key]?.length)) out.push('Explain what needs reframing.');
    return out;
  }
  globalThis.OwnerReviewContract = Object.freeze({ schema, dispositions, errors });
})();
