let currentPack = null;
let completedPack = null;
let loadSequence = 0;
const $ = id => document.getElementById(id);
const isIntake = pack => pack?.schema === OwnerReviewContract.schema;
const copy = value => structuredClone(value);
const intakeText = {
  intakeCorrections: 'factual_corrections', intakeConstraints: 'missing_constraints',
  safeguardingCorrections: 'access_or_safeguarding_corrections', fundingNotes: 'funding_or_resource_notes',
};

function invalidateResponse() {
  completedPack = null;
  $('copyResponse').disabled = true;
  $('saveResponse').disabled = true;
  $('responsePreviewPanel').classList.add('hidden');
  $('responsePreview').textContent = '';
}

function loadPack(pack) {
  validatePack(pack);
  currentPack = copy(pack);
  invalidateResponse();
  $('reviewForm').reset();
  renderPack(currentPack);
  $('reviewApp').classList.remove('hidden');
  $('loadStatus').textContent = `Loaded ${isIntake(pack) ? 'problem-owner' : pack.audience} review for ${pack.problem_id}. Existing answers have been restored.`;
}

$('packFile').addEventListener('change', async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  const sequence = ++loadSequence;
  currentPack = null;
  invalidateResponse();
  $('reviewApp').classList.add('hidden');
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error('Review files must be smaller than 2 MB.');
    const text = await file.text();
    if (sequence !== loadSequence) return;
    loadPack(JSON.parse(text));
  } catch (error) {
    if (sequence === loadSequence) $('loadStatus').textContent = `Could not load pack: ${error.message}`;
  }
});

$('reviewForm').addEventListener('input', () => {
  if (completedPack) {
    invalidateResponse();
    $('formStatus').textContent = 'Answers changed. Prepare the completed response again before saving it.';
  }
});
$('reviewForm').addEventListener('change', invalidateResponse);
$('intakeDisposition').addEventListener('change', () => {
  if ($('intakeDisposition').value === 'reframe') {
    $('intakeReframe').checked = true;
    $('correctionDetails').open = true;
  }
});

$('reviewForm').addEventListener('submit', event => {
  event.preventDefault();
  if (!currentPack) return;
  invalidateResponse();
  try {
    completedPack = collectResponse(currentPack, false);
    $('responsePreview').textContent = JSON.stringify(completedPack, null, 2);
    $('responsePreviewPanel').classList.remove('hidden');
    $('copyResponse').disabled = false;
    $('saveResponse').disabled = false;
    $('formStatus').textContent = 'Response prepared, not sent. Save the completed review and return it through the channel agreed with your curator.';
  } catch (error) { $('formStatus').textContent = error.message; }
});

$('saveDraft').addEventListener('click', () => {
  if (!currentPack) return;
  try {
    const draft = collectResponse(currentPack, true);
    saveJson(draft, 'draft');
    $('formStatus').textContent = 'Draft saved, not sent. Reopen it using the file picker to continue. Incomplete reviews remain undecided.';
  } catch (error) { $('formStatus').textContent = error.message; }
});
$('copyResponse').addEventListener('click', async () => {
  if (!completedPack) return;
  try {
    await navigator.clipboard.writeText(JSON.stringify(completedPack, null, 2));
    $('formStatus').textContent = 'Completed response copied. Nothing has been sent.';
  } catch { $('formStatus').textContent = 'Clipboard unavailable. Use Save response JSON instead.'; }
});
$('saveResponse').addEventListener('click', () => {
  if (!completedPack) return;
  saveJson(completedPack, 'completed');
  $('formStatus').textContent = 'Completed review saved, not sent. Return this file to the curator.';
});
function saveJson(pack, suffix) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(pack, null, 2) + '\n'], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = url; a.download = `${sanitize(pack.problem_id)}-${suffix}-review.json`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function validatePack(pack) {
  if (isIntake(pack)) {
    const errors = OwnerReviewContract.errors(pack);
    if (errors.length) throw new Error(errors.join(' '));
    return;
  }
  if (!pack || pack.schema !== 'problem-review-pack/v0.1') throw new Error('Unsupported review-pack schema.');
  if (!['owner', 'reviewer', 'solver'].includes(pack.audience)) throw new Error('Invalid review audience.');
  if (!pack.problem_id || !pack.problem || pack.problem.id !== pack.problem_id) throw new Error('Problem identity mismatch.');
  if (!pack.rubric || !Array.isArray(pack.rubric.items) || !pack.rubric.items.length) throw new Error('Review pack has no rubric items.');
  if (!pack.response || !Array.isArray(pack.response.item_scores) || pack.response.item_scores.length !== pack.rubric.items.length) throw new Error('Review pack has no valid response template.');
}

function renderPack(pack) {
  const intake = isIntake(pack), p = pack.problem, r = pack.response;
  $('audienceLabel').textContent = intake ? 'PROBLEM-OWNER REVIEW' : `${pack.audience.toUpperCase()} REVIEW`;
  $('problemTitle').textContent = p.title || 'Untitled problem';
  $('problemStatus').textContent = intake ? 'Awaiting review · not open for work' : p.status || 'unknown';
  $('ownerContext').textContent = intake ? `Potential owner: ${pack.potential_owner} · ${p.geography || 'Location to confirm'}` : '';
  $('sourceContext').replaceChildren();
  if (intake && pack.source_ref) {
    try {
      const url = new URL(pack.source_ref);
      if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) {
        const a = document.createElement('a'); a.href = url.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
        a.textContent = 'Open the public source'; $('sourceContext').appendChild(a);
      }
    } catch { /* A private/invalid locator is never made executable. */ }
  }
  $('privacyNote').textContent = pack.privacy_note || '';
  $('observedCondition').textContent = p.observed_condition || 'Not specified.';
  $('unresolvedCore').textContent = p.unresolved_core || 'Not specified.';
  $('authorityBoundary').textContent = p.authority_boundary || 'Not specified.';
  renderList($('uncertaintyList'), intake ? p.uncertainties : p.disputes_uncertainty || [], 'No explicit uncertainty items provided.');
  renderList($('instructions'), pack.instructions || [], 'No instructions provided.');
  $('rubricName').textContent = intake ? 'Your review' : humanize(pack.rubric.name || 'review rubric');
  $('rubricScoring').textContent = intake ? 'Mark each statement Yes or No. A No is useful feedback, not a failed review.' : pack.rubric.scoring || '';
  $('rubricItems').replaceChildren();
  pack.rubric.items.forEach((item, i) => {
    const row = document.createElement('fieldset'); row.className = 'rubric-item'; row.style.border = '0';
    const legend = document.createElement('legend'); legend.textContent = `${i + 1}. ${item}`; row.appendChild(legend);
    const choices = document.createElement('div'); choices.className = 'score-row';
    [1, 0].forEach(value => {
      const label = document.createElement('label'), input = document.createElement('input');
      input.type = 'radio'; input.name = `score-${i}`; input.value = String(value); input.checked = r.item_scores[i] === value;
      label.append(input, document.createTextNode(value ? ' Yes / supported' : ' No / not supported')); choices.appendChild(label);
    });
    row.appendChild(choices); $('rubricItems').appendChild(row);
  });
  $('intakeIdentityFields').classList.toggle('hidden', !intake);
  $('intakeReviewFields').classList.toggle('hidden', !intake);
  $('standardReviewFields').classList.toggle('hidden', intake);
  $('ownerReviewerFields').classList.toggle('hidden', intake || pack.audience === 'solver');
  $('solverFields').classList.toggle('hidden', intake || pack.audience !== 'solver');
  $('stageSummary').parentElement.classList.toggle('hidden', intake);
  $('stageSummary').replaceChildren();
  $('formStatus').textContent = '';
  if (intake) {
    $('sourceCurrent').value = r.source_still_current === null ? '' : r.source_still_current ? 'yes' : 'no';
    $('ownerCorrect').value = r.owner_identity_and_role_correct === null ? '' : r.owner_identity_and_role_correct ? 'yes' : 'no';
    for (const [id, key] of Object.entries(intakeText)) $(id).value = r[key].join('\n');
    $('desiredOutcome').value = r.desired_outcome_or_priority;
    $('correctionDetails').open = Object.values(intakeText).some(key => r[key].length) || Boolean(r.desired_outcome_or_priority);
    $('intakeNotes').value = r.owner_notes;
    $('intakeReframe').checked = r.reframe_required;
    $('intakeDisposition').value = r.disposition;
    $('workChoices').replaceChildren();
    p.candidate_work.forEach((work, i) => {
      const card = document.createElement('article'); card.className = 'work-choice';
      const title = document.createElement('h4'); title.textContent = work.title; card.appendChild(title);
      for (const text of [work.description, `Expected output: ${work.expected_outputs.join('; ') || 'To agree'}`, `Effort: ${work.effort || 'To agree'}`, ...(work.required_credentials.length ? [`Required qualification: ${work.required_credentials.join('; ')}`] : [])]) {
        const line = document.createElement('p'); line.textContent = text; card.appendChild(line);
      }
      const label = document.createElement('label'); label.textContent = 'Is this useful to explore?';
      const select = document.createElement('select'); select.id = `work-choice-${i}`; select.dataset.workId = work.subproblem_id;
      for (const [value, text] of [['', 'Not assessed'], ['explore', 'Yes — explore during curation'], ['stop', 'No — do not proceed']]) {
        const option = document.createElement('option'); option.value = value; option.textContent = text; select.appendChild(option);
      }
      select.value = r.acceptable_work_subproblem_ids.includes(work.subproblem_id) ? 'explore' : r.unacceptable_work_subproblem_ids.includes(work.subproblem_id) ? 'stop' : '';
      label.appendChild(select); card.appendChild(label); $('workChoices').appendChild(card);
    });
    if (!p.candidate_work.length) $('workChoices').textContent = 'No work has been proposed. Your corrections will help the curator identify a useful first task.';
    return;
  }
  for (const profile of pack.stage_profiles || []) {
    const card = document.createElement('article'); card.className = 'review-card';
    card.innerHTML = `<p class="eyebrow">${escapeHtml(profile.stage || 'stage')}</p><h3>${escapeHtml(profile.question || profile.subproblem_id || 'Contribution')}</h3><p>${escapeHtml(profile.work_mode || '')}</p><small>${escapeHtml((profile.expected_outputs || []).join(' · '))}</small>`;
    $('stageSummary').appendChild(card);
  }
  if (!(pack.stage_profiles || []).length) $('stageSummary').textContent = 'No stage profiles are exposed for this pack.';
  $('selectedSubproblem').replaceChildren(new Option('No path selected', ''));
  (p.subproblems || []).forEach(sub => $('selectedSubproblem').appendChild(new Option(`${sub.title} (${sub.kind})`, sub.id)));
  for (const [id, key] of [['disagreements', 'disagreement_notes'], ['materialErrors', 'material_errors']]) $(id).value = (r[key] || []).join('\n');
  for (const [id, key] of [['coachingReceived', 'coaching_received'], ['reframeRequired', 'reframe_required'], ['seriousAttempt', 'serious_attempt'], ['abandoned', 'abandoned']]) $(id).checked = r[key] === true;
  for (const [id, key] of [['reviewNotes', 'review_notes'], ['minutesToEdge', 'minutes_to_useful_edge'], ['usefulness', 'usefulness_rating'], ['abandonmentReason', 'abandonment_reason'], ['observerNotes', 'observer_notes'], ['selectedSubproblem', 'selected_subproblem_id']]) $(id).value = r[key] ?? '';
  $('publishRecommendation').value = r.publish_recommendation || 'undecided';
}

function collectResponse(pack, draft) {
  const result = copy(pack), r = result.response;
  r.item_scores = pack.rubric.items.map((_, i) => {
    const selected = document.querySelector(`input[name="score-${i}"]:checked`);
    if (!selected && !draft) throw new Error(`Answer review item ${i + 1} before preparing the completed response.`);
    return selected ? Number(selected.value) : null;
  });
  if (isIntake(pack)) {
    r.source_still_current = optionalBool($('sourceCurrent').value);
    r.owner_identity_and_role_correct = optionalBool($('ownerCorrect').value);
    for (const [id, key] of Object.entries(intakeText)) r[key] = lines($(id).value);
    r.desired_outcome_or_priority = $('desiredOutcome').value.trim(); r.owner_notes = $('intakeNotes').value.trim();
    r.reframe_required = $('intakeReframe').checked; r.disposition = $('intakeDisposition').value;
    r.acceptable_work_subproblem_ids = []; r.unacceptable_work_subproblem_ids = [];
    $('workChoices').querySelectorAll('select').forEach(select => {
      if (select.value === 'explore') r.acceptable_work_subproblem_ids.push(select.dataset.workId);
      if (select.value === 'stop') r.unacceptable_work_subproblem_ids.push(select.dataset.workId);
    });
    if (draft && OwnerReviewContract.errors(result).length) r.disposition = 'undecided';
    const errors = OwnerReviewContract.errors(result, !draft);
    if (errors.length) throw new Error(errors.join(' '));
    return result;
  }
  r.disagreement_notes = lines($('disagreements').value); r.material_errors = lines($('materialErrors').value);
  r.coaching_received = $('coachingReceived').checked;
  if (pack.audience === 'solver') {
    r.selected_subproblem_id = $('selectedSubproblem').value || null;
    if ($('seriousAttempt').checked && !r.selected_subproblem_id && !draft) throw new Error('A serious attempt must identify a contribution path.');
    r.minutes_to_useful_edge = optionalNumber($('minutesToEdge').value, 0, Infinity, 'Minutes to useful edge');
    r.usefulness_rating = optionalNumber($('usefulness').value, 0, 1, 'Usefulness rating');
    r.serious_attempt = $('seriousAttempt').checked; r.abandoned = $('abandoned').checked;
    r.abandonment_reason = $('abandonmentReason').value.trim(); r.observer_notes = $('observerNotes').value.trim();
    r.arm = r.arm || 'problem_packet';
  } else {
    r.reframe_required = $('reframeRequired').checked; r.publish_recommendation = $('publishRecommendation').value;
    r.review_notes = $('reviewNotes').value.trim();
  }
  return result;
}
function optionalBool(value) { return value === '' ? null : value === 'yes'; }
function optionalNumber(raw, min, max, label) {
  if (raw === '') return null;
  const value = Number(raw);
  if (!Number.isFinite(value) || value < min || value > max) throw new Error(`${label} is out of range.`);
  return value;
}
function lines(value) { return value.split(/\r?\n/).map(item => item.trim()).filter(Boolean); }
function renderList(root, values, fallback) {
  root.replaceChildren();
  (values?.length ? values : [fallback]).forEach(value => { const li = document.createElement('li'); li.textContent = value; root.appendChild(li); });
}
function humanize(value) { return value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase()); }
function sanitize(value) { return value.replace(/[^a-z0-9._-]+/gi, '-').replace(/^-+|-+$/g, ''); }
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]); }

const preloaded = document.getElementById('preloadedReview');
if (preloaded) {
  try { loadPack(JSON.parse(preloaded.textContent)); }
  catch (error) { $('loadStatus').textContent = `Could not load embedded review: ${error.message}`; }
}
