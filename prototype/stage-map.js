const stages = [
  ['observe','What is happening?'],
  ['measure','How large or recurrent?'],
  ['explain','What mechanism?'],
  ['design','What should we test/build?'],
  ['build','Can it be implemented?'],
  ['test','Does it survive evaluation?'],
  ['deploy','Can authority execute it?'],
  ['monitor','What happened afterward?'],
  ['generalize','What can be reused?']
];

const problemSelect = document.querySelector('#problemSelect');
const stageRail = document.querySelector('#stageRail');
const profileCards = document.querySelector('#profileCards');
const problemHeader = document.querySelector('#problemHeader');
const coverage = document.querySelector('#coverage');
let problems = [];
let profiles = [];
let selectedProblem = '';
let selectedStage = 'all';

const esc = (value = '') => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label = value => String(value).replaceAll('-', ' ').replaceAll('_',' ').replace(/\b\w/g, c => c.toUpperCase());

function workMode(profile){
  if (profile.uncertainty === 'frontier' || profile.method_maturity === 'novel') return 'research-frontier';
  if (['measure','explain','test'].includes(profile.stage) && ['high','frontier'].includes(profile.uncertainty)) return 'empirical-inquiry';
  if (['adaptable','experimental'].includes(profile.method_maturity) || profile.uncertainty === 'medium') return 'adaptive-practice';
  return 'known-practice';
}

function renderRail(){
  const rows = profiles.filter(p => p.problem_id === selectedProblem);
  const counts = Object.fromEntries(stages.map(([stage]) => [stage, rows.filter(p => p.stage === stage).length]));
  stageRail.innerHTML = stages.map(([stage, description]) => `
    <button class="stage ${selectedStage === stage ? 'active' : ''}" data-stage="${stage}" type="button">
      <strong>${esc(label(stage))}${counts[stage] ? ` · ${counts[stage]}` : ''}</strong>
      <span>${esc(description)}</span>
    </button>`).join('');
  stageRail.querySelectorAll('[data-stage]').forEach(button => button.addEventListener('click', () => {
    selectedStage = selectedStage === button.dataset.stage ? 'all' : button.dataset.stage;
    render();
  }));
}

function findSubproblem(problem, id){
  return (problem?.subproblems || []).find(row => row.id === id);
}

function renderProblem(){
  const problem = problems.find(row => row.id === selectedProblem);
  const rows = profiles.filter(p => p.problem_id === selectedProblem);
  const stageCount = new Set(rows.map(row => row.stage)).size;
  coverage.textContent = `${rows.length} contribution profiles · ${stageCount}/9 stages currently represented`;
  problemHeader.innerHTML = problem ? `
    <div class="kicker">${esc(problem.id)} · ${esc(problem.status)}</div>
    <h2>${esc(problem.title)}</h2>
    <div class="problem-meta"><span class="pill">${esc(problem.domain)}</span><span class="pill">${esc(problem.geography)}</span></div>
    <p>${esc(problem.unresolved_core)}</p>` : '<div class="empty">Problem metadata unavailable.</div>';
}

function renderProfiles(){
  const problem = problems.find(row => row.id === selectedProblem);
  const rows = profiles
    .filter(row => row.problem_id === selectedProblem)
    .filter(row => selectedStage === 'all' || row.stage === selectedStage);
  if (!rows.length) {
    profileCards.innerHTML = `<div class="empty">No contribution path is currently classified at ${selectedStage === 'all' ? 'this problem' : `the ${esc(label(selectedStage))} stage`}. Missing stages are allowed; the model is not a mandatory waterfall.</div>`;
    return;
  }
  profileCards.innerHTML = rows.map(profile => {
    const sub = findSubproblem(problem, profile.subproblem_id);
    const authority = profile.authority_level !== 'none' ? `<div class="authority"><b>${esc(label(profile.authority_level))} authority:</b> ${esc(profile.authority_requirement || 'Review/authority requirement must be specified.')}</div>` : '';
    return `
      <section class="card">
        <div class="card-head">
          <div><div class="kicker">${esc(label(profile.stage))} · ${esc(profile.epistemic_type)}</div><h3>${esc(sub?.title || profile.subproblem_id)}</h3></div>
          <span class="mode">${esc(label(workMode(profile)))}</span>
        </div>
        <div class="question">${esc(profile.question)}</div>
        <div class="facts">
          <div class="fact"><b>Uncertainty</b><span>${esc(label(profile.uncertainty))}</span></div>
          <div class="fact"><b>Method maturity</b><span>${esc(label(profile.method_maturity))}</span></div>
          <div class="fact"><b>Expected output</b><span>${esc((profile.expected_outputs || []).join(' · '))}</span></div>
          <div class="fact"><b>Evaluation</b><span>${esc(profile.evaluation_method)}</span></div>
          <div class="fact"><b>Reuse target</b><span>${esc(profile.reuse_target || 'Not yet specified')}</span></div>
          <div class="fact"><b>Credentials</b><span>${esc((profile.required_credentials || []).join(' · ') || 'No formal credential gate')}</span></div>
        </div>
        <div class="routes">${(profile.system_routes || []).map(system => `<span class="route">${esc(label(system))}</span>`).join('')}</div>
        ${authority}
      </section>`;
  }).join('');
}

function render(){
  renderRail();
  renderProblem();
  renderProfiles();
}

async function boot(){
  const [problemResponse, stageResponse] = await Promise.all([fetch('problems.json'), fetch('stage-profiles.json')]);
  if (!problemResponse.ok || !stageResponse.ok) throw new Error('Could not load prototype data.');
  problems = await problemResponse.json();
  profiles = (await stageResponse.json()).profiles || [];
  const ids = [...new Set(profiles.map(row => row.problem_id))];
  problemSelect.innerHTML = ids.map(id => {
    const p = problems.find(row => row.id === id);
    return `<option value="${esc(id)}">${esc(p?.title || id)}</option>`;
  }).join('');
  selectedProblem = ids[0] || '';
  problemSelect.value = selectedProblem;
  problemSelect.addEventListener('change', () => {
    selectedProblem = problemSelect.value;
    selectedStage = 'all';
    render();
  });
  render();
}

boot().catch(error => {
  problemHeader.innerHTML = `<div class="empty">${esc(error.message)}</div>`;
  console.error(error);
});
