const list = document.querySelector('#problemList');
const detail = document.querySelector('#problemDetail');
const search = document.querySelector('#search');
const statusFilter = document.querySelector('#statusFilter');
let problems = [];
let selected = null;

const esc = (value = '') => String(value).replace(/[&<>'\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[c]));
const label = value => value.replaceAll('_',' ').replace(/\b\w/g, c => c.toUpperCase());

function filteredProblems(){
  const q = search.value.trim().toLowerCase();
  const state = statusFilter.value;
  return problems.filter(p => (state === 'all' || p.status === state) && (!q || [p.title,p.domain,p.geography,p.unresolved_core].join(' ').toLowerCase().includes(q)));
}

function renderList(){
  const data = filteredProblems();
  list.innerHTML = data.map(p => `
    <div class="problem-card ${selected === p.id ? 'active' : ''}" data-id="${esc(p.id)}">
      <div class="card-top"><span class="domain">${esc(p.domain)}</span><span class="status">${esc(label(p.status))}</span></div>
      <h3>${esc(p.title)}</h3>
      <div class="meta"><span>${esc(p.geography)}</span><span>•</span><span>${p.subproblems.length} contribution paths</span><span>•</span><span>${p.attempts.length} attempts</span></div>
    </div>`).join('') || '<div class="problem-card">No problems match this filter.</div>';
  list.querySelectorAll('[data-id]').forEach(card => card.addEventListener('click', () => selectProblem(card.dataset.id)));
}

function selectProblem(id){
  selected = id;
  const p = problems.find(item => item.id === id);
  renderList();
  detail.classList.remove('empty');
  detail.innerHTML = `
    <div class="detail-head">
      <div><div class="kicker">${esc(p.id)} · updated ${esc(p.updated)}</div><h2>${esc(p.title)}</h2><div class="meta"><span>${esc(p.domain)}</span><span>•</span><span>${esc(p.geography)}</span><span>•</span><span>${esc(label(p.status))}</span></div></div>
      <span class="confidence">${esc(p.confidence)}</span>
    </div>
    <div class="detail-grid">
      <div>
        <section class="section"><h4>Observed condition</h4><p>${esc(p.observed_condition)}</p></section>
        <section class="section callout"><h4>What remains unsolved</h4><p>${esc(p.unresolved_core)}</p></section>
        <section class="section"><h4>Knowledge frontier</h4><ul>${p.knowledge_frontier.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></section>
        <section class="section"><h4>Where you can contribute</h4>${p.subproblems.map(s=>`<div class="subproblem"><small>${esc(s.kind)} · ${esc(s.id)}</small><strong>${esc(s.title)}</strong><p>${esc(s.detail)}</p></div>`).join('')}<div class="action-row"><button class="action" onclick="alert('V0: this would create a private Attempt branch attached to the selected subproblem.')">Start an attempt</button><button class="action secondary" onclick="alert('V0: this would open Cite against the problem evidence and unresolved frontier.')">Research this problem</button></div></section>
      </div>
      <aside>
        <section class="section"><h4>Capability frontier</h4>${p.capabilities.map(c=>`<div class="capability"><span>${esc(c.name)}</span><b class="${esc(c.state)}">${esc(c.state)}</b></div>`).join('')}</section>
        <section class="section"><h4>Success means</h4><p>${esc(p.success)}</p></section>
        <section class="section"><h4>Authority boundary</h4><p>${esc(p.authority)}</p></section>
        <section class="section"><h4>Affected actors</h4><p>${p.affected.map(esc).join(' · ')}</p></section>
        <section class="section"><h4>Living history</h4><div class="timeline">${p.history.map(h=>`<div><strong>${esc(h.label)}</strong><small>${esc(h.date)}</small></div>`).join('')}</div></section>
      </aside>
    </div>`;
}

async function boot(){
  const response = await fetch('problems.json');
  if (!response.ok) throw new Error(`Failed to load problems: ${response.status}`);
  problems = await response.json();
  document.querySelector('#problemCount').textContent = problems.length;
  renderList();
  if (problems.length) selectProblem(problems[0].id);
}

search.addEventListener('input', renderList);
statusFilter.addEventListener('change', renderList);
boot().catch(error => { detail.innerHTML = `<p>${esc(error.message)}</p>`; console.error(error); });
