const select = document.getElementById('envelopeSelect');
const view = document.getElementById('governanceView');
let envelopes = [];

const requiredByTarget = {
  review: ['evidence','safety','integrity','rights'],
  test: ['evidence','safety','integrity','rights','data-access','reversibility'],
  deploy: ['evidence','safety','integrity','rights','data-access','reversibility','authority']
};

function gateFor(item, kind){ return (item.gates || []).find(g => g.kind === kind); }
function readiness(item, target){
  const blockers = [];
  const requiredText = ['problem_id','subproblem_id','title','target_transition','diagnosis_hypothesis','intervention_class','smallest_feasible_change','expected_mechanism','monitoring_plan'];
  requiredText.forEach(k => { if(!String(item[k] || '').trim()) blockers.push(`missing ${k.replaceAll('_',' ')}`); });
  if(!(item.evidence_refs || []).length) blockers.push('no evidence refs attached');
  if(!(item.outcome_metrics || []).length) blockers.push('no outcome metrics defined');
  if(item.reversibility === 'unknown') blockers.push('reversibility is unknown');
  if(['reversible','partially-reversible'].includes(item.reversibility) && !item.rollback_plan) blockers.push('rollback plan missing');
  requiredByTarget[target].forEach(kind => {
    const g = gateFor(item, kind);
    if(!g) blockers.push(`missing ${kind} gate`);
    else if(g.status === 'pending' || g.status === 'failed') blockers.push(`${kind} gate ${g.status}`);
  });
  const professional = gateFor(item, 'professional');
  if(professional && ['pending','failed'].includes(professional.status)) blockers.push(`professional gate ${professional.status}`);
  if(target === 'deploy'){
    const goodTest = (item.tests || []).some(t => t.passed && !(t.guardrail_breaches || []).length);
    if(!goodTest) blockers.push('no passed guardrail-safe test receipt');
    if(!item.authority_actor || !item.authority_scope) blockers.push('named external authority and scope required');
  }
  return {ready: blockers.length === 0, blockers};
}
function esc(v){ return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function tags(values){ return `<div class="tags">${(values||[]).map(v=>`<em>${esc(v)}</em>`).join('') || '<span>None recorded</span>'}</div>`; }
function readyCard(label, r){ return `<div class="ready-card"><span>${label}</span><b class="${r.ready?'status-satisfied':'status-pending'}">${r.ready?'Ready':'Blocked'}</b>${r.blockers.length?`<ul class="blocked-list">${r.blockers.slice(0,5).map(b=>`<li>${esc(b)}</li>`).join('')}</ul>`:'<small>No blocking gate.</small>'}</div>`; }

function render(item){
  const review = readiness(item,'review'), test = readiness(item,'test'), deploy = readiness(item,'deploy');
  view.className = 'gov-grid';
  view.innerHTML = `
    <section class="gov-panel">
      <p class="eyebrow">INTERVENTION ENVELOPE · ${esc(item.state)}</p>
      <h2>${esc(item.title)}</h2>
      <p class="note"><strong>Not authority:</strong> this is a reviewed intervention projection. Real deployment still belongs to the competent external actor.</p>
      <div class="readiness">${readyCard('Review',review)}${readyCard('Test',test)}${readyCard('Deploy',deploy)}</div>
      <div class="facts">
        <div class="fact"><span>Target transition</span>${esc(item.target_transition)}</div>
        <div class="fact"><span>Intervention class</span>${esc(item.intervention_class)}</div>
        <div class="fact"><span>Diagnosis hypothesis</span>${esc(item.diagnosis_hypothesis)}</div>
        <div class="fact"><span>Expected mechanism</span>${esc(item.expected_mechanism)}</div>
        <div class="fact"><span>Smallest feasible change</span>${esc(item.smallest_feasible_change)}</div>
        <div class="fact"><span>Reversibility</span>${esc(item.reversibility)}${item.rollback_plan?`<small> · rollback: ${esc(item.rollback_plan)}</small>`:''}</div>
      </div>
      <h3>Governance gates</h3>
      <div class="gate-grid">${(item.gates||[]).map(g=>`<div class="gate"><strong><span>${esc(g.kind)}</span><span class="status-${esc(g.status)}">${esc(g.status)}</span></strong><small>${esc(g.requirement || 'No requirement recorded')}</small>${g.reviewer?`<small>Reviewed by ${esc(g.reviewer)}</small>`:''}</div>`).join('')}</div>
    </section>
    <aside class="gov-panel">
      <h3>Why this is bounded</h3>
      <div class="fact"><span>Problem</span>${esc(item.problem_id)}</div>
      <div class="fact"><span>Contribution</span>${esc(item.subproblem_id)}</div>
      <div class="fact"><span>Public-Good source</span>${esc(item.public_good_ref || 'No source projection linked')}</div>
      <div class="fact"><span>Preconditions</span>${tags(item.preconditions)}</div>
      <div class="fact"><span>Constraints</span>${tags(item.constraints)}</div>
      <div class="fact"><span>Rights impacts</span>${tags(item.rights_impacts)}</div>
      <div class="fact"><span>Safety risks</span>${tags(item.safety_risks)}</div>
      <div class="fact"><span>Integrity risks</span>${tags(item.integrity_risks)}</div>
      <div class="fact"><span>Outcome metrics</span>${tags(item.outcome_metrics)}</div>
      <div class="fact"><span>Monitoring</span>${esc(item.monitoring_plan)}</div>
      <div class="fact"><span>External authority</span>${item.authority_actor?`${esc(item.authority_actor)} · ${esc(item.authority_scope)}`:'Not yet granted'}</div>
      <div class="fact"><span>Test receipts</span>${(item.tests||[]).length?esc(item.tests.map(t=>`${t.passed?'pass':'fail'}: ${t.summary}`).join(' · ')):'None yet'}</div>
    </aside>`;
}

fetch('governance-envelopes.json').then(r=>r.json()).then(data=>{
  envelopes = data.envelopes || [];
  select.innerHTML = envelopes.map((item,i)=>`<option value="${i}">${esc(item.title)}</option>`).join('');
  if(envelopes.length) render(envelopes[0]); else view.textContent='No governance envelopes.';
  select.addEventListener('change',()=>render(envelopes[Number(select.value)]));
}).catch(err=>{ view.textContent = `Could not load governance envelopes: ${err.message}`; });
