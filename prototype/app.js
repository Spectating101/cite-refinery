const PUBLIC_STATES = new Set(["verified","open","partially_resolved","piloting","deployed","monitoring","resolved"]);
const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => [...root.querySelectorAll(sel)];
const esc = (value="") => String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const label = value => String(value || "").replaceAll("_"," ").replace(/\b\w/g, c => c.toUpperCase());

let problems = [];
let selectedId = null;
let activeTab = "overview";
let stewardMode = false;

function localAttempts(){
  try { return JSON.parse(localStorage.getItem("pc-v01-attempts") || "[]"); } catch { return []; }
}
function localCandidates(){
  try { return JSON.parse(localStorage.getItem("pc-v01-candidates") || "[]"); } catch { return []; }
}
function saveLocal(key, value){ localStorage.setItem(key, JSON.stringify(value)); }
function toast(message){
  const node = $("#toast"); node.textContent = message; node.classList.add("show");
  clearTimeout(toast.timer); toast.timer = setTimeout(() => node.classList.remove("show"), 2600);
}

function publicProblems(){ return problems.filter(p => PUBLIC_STATES.has(p.status)); }
function allAttemptsFor(p){
  const local = localAttempts().filter(x => x.problem_id === p.id);
  return [...(p.attempts || []), ...local];
}
function filteredProblems(){
  const q = $("#search").value.trim().toLowerCase();
  const domain = $("#domainFilter").value;
  const status = $("#statusFilter").value;
  return publicProblems().filter(p => {
    if(domain !== "all" && p.domain !== domain) return false;
    if(status !== "all" && p.status !== status) return false;
    const hay = [
      p.title,p.summary,p.domain,p.geography,p.unresolved_core,
      ...(p.knowledge_frontier || []),
      ...(p.capabilities || []).flatMap(c => [c.name,c.description]),
      ...(p.subproblems || []).flatMap(s => [s.title,s.detail,...(s.skills||[])])
    ].join(" ").toLowerCase();
    return !q || hay.includes(q);
  });
}

function renderMetrics(){
  const pubs = publicProblems();
  $("#problemCount").textContent = pubs.length;
  $("#contributionCount").textContent = pubs.reduce((n,p)=>n+(p.subproblems||[]).filter(s=>s.status!=="closed").length,0);
  $("#attemptCount").textContent = pubs.reduce((n,p)=>n+allAttemptsFor(p).length,0);
  $("#outcomeCount").textContent = pubs.reduce((n,p)=>n+(p.outcomes||[]).length,0);
}

function renderDomainFilter(){
  const domains = [...new Set(publicProblems().map(p=>p.domain))].sort();
  $("#domainFilter").innerHTML = `<option value="all">All domains</option>${domains.map(d=>`<option value="${esc(d)}">${esc(d)}</option>`).join("")}`;
}

function renderList(){
  const data = filteredProblems();
  $("#problemList").innerHTML = data.map(p => `
    <div class="problem-card ${selectedId===p.id?"active":""}" data-id="${esc(p.id)}" tabindex="0">
      <div class="card-top"><span class="domain">${esc(p.domain)}</span><span class="status">${esc(label(p.status))}</span></div>
      <h3>${esc(p.title)}</h3>
      <p class="card-summary">${esc(p.summary || p.unresolved_core)}</p>
      <div class="meta">
        <span>${esc(p.geography || "Multi-location")}</span>
        <span>·</span>
        <span>${(p.subproblems||[]).length} paths</span>
        <span>·</span>
        <span>${allAttemptsFor(p).length} attempts</span>
      </div>
    </div>`).join("") || `<div class="empty-state">No public problems match these filters.</div>`;
  $$(".problem-card[data-id]").forEach(card => {
    card.addEventListener("click", () => selectProblem(card.dataset.id));
    card.addEventListener("keydown", e => { if(e.key==="Enter") selectProblem(card.dataset.id); });
  });
}

function selectProblem(id){
  selectedId = id;
  activeTab = "overview";
  renderList();
  renderDetail();
}

function currentProblem(){ return problems.find(p=>p.id===selectedId); }

function renderDetail(){
  const p = currentProblem();
  const detail = $("#problemDetail");
  if(!p){ detail.className="detail empty"; detail.innerHTML="<p>Select a problem to inspect its living packet.</p>"; return; }
  detail.className = "detail";
  detail.innerHTML = `
    <header class="detail-head">
      <div>
        <div class="kicker">${esc(p.id)} · updated ${esc(p.updated || "—")}</div>
        <h2>${esc(p.title)}</h2>
        <div class="meta"><span>${esc(p.domain)}</span><span>·</span><span>${esc(p.geography||"Multi-location")}</span><span>·</span><span>${esc(p.owner||"Owner not specified")}</span></div>
      </div>
      <div class="head-badges"><span class="confidence">${esc(p.confidence||"Curated")}</span><span class="state-badge">${esc(label(p.status))}</span></div>
    </header>
    <div class="tabs">
      ${tabButton("overview","Overview")}
      ${tabButton("contribute","Contribute")}
      ${tabButton("evidence","Evidence & prior art")}
      ${tabButton("attempts","Attempts & outcomes")}
      ${tabButton("steward","Steward","steward-only")}
    </div>
    <div id="tabPanel" class="tab-panel"></div>`;
  bindTabs();
  renderTab();
}

function tabButton(id, text, cls=""){
  return `<button class="tab ${activeTab===id?"active":""} ${cls}" data-tab="${id}">${text}</button>`;
}
function bindTabs(){
  $$(".tab").forEach(btn=>btn.addEventListener("click",()=>{activeTab=btn.dataset.tab; $$(".tab").forEach(x=>x.classList.toggle("active",x===btn)); renderTab();}));
}

function renderTab(){
  const p = currentProblem(); if(!p) return;
  const panel = $("#tabPanel");
  if(activeTab==="overview") panel.innerHTML = renderOverview(p);
  if(activeTab==="contribute") panel.innerHTML = renderContribute(p);
  if(activeTab==="evidence") panel.innerHTML = renderEvidence(p);
  if(activeTab==="attempts") panel.innerHTML = renderAttempts(p);
  if(activeTab==="steward") panel.innerHTML = renderSteward(p);
  bindDynamicActions(p);
}

function renderOverview(p){
  return `<div class="two-col">
    <div>
      <section class="section"><h4>Observed condition</h4><p>${esc(p.observed_condition)}</p></section>
      <section class="section callout"><h4>What remains unsolved</h4><p>${esc(p.unresolved_core)}</p></section>
      <section class="section"><h4>Working diagnosis — not assumed truth</h4>${(p.diagnosis||[]).map(x=>`<div class="hypothesis">${esc(x)}</div>`).join("") || `<div class="empty-state">Diagnosis remains deliberately open.</div>`}</section>
      <section class="section"><h4>Knowledge frontier</h4>${bulletList(p.knowledge_frontier)}</section>
      <section class="section"><h4>Previous attempts / known approaches</h4>${bulletList(p.prior_attempts)}</section>
      <section class="section"><h4>Success and falsification</h4>${(p.success||[]).map(s=>`
        <div class="success-card"><strong>${esc(s.metric)}</strong>
          <dl><dt>Baseline</dt><dd>${esc(s.baseline||"To be frozen")}</dd><dt>Target</dt><dd>${esc(s.target)}</dd><dt>Measurement</dt><dd>${esc(s.measurement)}</dd><dt>Failure means</dt><dd>${esc(s.falsification)}</dd></dl>
          ${(s.guardrails||[]).map(g=>`<span class="guardrail">${esc(g)}</span>`).join("")}
        </div>`).join("")}</section>
    </div>
    <aside>
      <section class="section"><h4>Capability frontier</h4>${(p.capabilities||[]).map(c=>`
        <div class="capability"><span>${esc(c.name)}</span><b class="cap-state ${esc(c.state)}">${esc(c.state)}</b><small>${esc(c.description||"")}${c.limitations?.length?` · Limits: ${esc(c.limitations.join("; "))}`:""}</small></div>`).join("")}</section>
      <section class="section"><h4>Affected / benefiting actors</h4><p>${esc((p.affected||[]).join(" · "))}</p><p><strong>Potential beneficiaries:</strong> ${esc((p.beneficiaries||[]).join(" · ")||"Not specified")}</p></section>
      <section class="section"><h4>Constraints</h4>${bulletList(p.constraints)}</section>
      <section class="section"><h4>Authority boundary</h4><p>${esc(p.authority)}</p></section>
      <section class="section"><h4>Implementation pathway</h4>${bulletList(p.implementation_pathway)}</section>
      <section class="section"><button class="secondary-button" data-action="research">Research with Cite</button> <button class="secondary-button" data-action="capabilities">Inspect capability commons</button></section>
    </aside>
  </div>`;
}

function renderContribute(p){
  return `
    <section class="matcher">
      <p class="eyebrow">CONTRIBUTION MATCHER</p>
      <h3>Find a useful edge from what you can do.</h3>
      <div class="matcher-grid">
        <input id="matchSkills" placeholder="Skills: Python, statistics, interviews…" />
        <input id="matchInterests" placeholder="Interests: mobility, animals, policy…" />
        <button id="runMatch" class="primary-button">Match me</button>
      </div>
      <div id="matchResults" class="match-results"><span class="match-chip">No credential required unless a path explicitly says so.</span></div>
    </section>
    <section class="section">
      <h4>Open contribution paths</h4>
      ${(p.subproblems||[]).map(s=>renderSubproblem(p,s)).join("") || `<div class="empty-state">No contribution paths are open yet.</div>`}
    </section>`;
}
function renderSubproblem(p,s){
  const gates = s.required_credentials || [];
  return `<div class="subproblem" data-subproblem="${esc(s.id)}">
    <div class="subproblem-top"><div><small>${esc(s.kind)} · ${esc(s.id)} · ${esc(s.effort||"effort unspecified")}</small><h3>${esc(s.title)}</h3></div><button class="contribute-button" data-action="attempt" data-subproblem="${esc(s.id)}">Start attempt</button></div>
    <p>${esc(s.detail)}</p>
    <div class="tag-row">
      ${(s.skills||[]).map(x=>`<span class="tag">${esc(x)}</span>`).join("")}
      ${(s.interests||[]).map(x=>`<span class="tag">${esc(x)}</span>`).join("")}
      ${gates.map(x=>`<span class="tag gate">requires ${esc(x)}</span>`).join("")}
    </div>
    ${(s.outputs||[]).length?`<p><strong>Useful outputs:</strong> ${esc(s.outputs.join(" · "))}</p>`:""}
  </div>`;
}

function renderEvidence(p){
  return `<div class="two-col">
    <div>
      <section class="section"><h4>Evidence supporting the observed condition</h4>
        ${(p.evidence||[]).map(e=>`<div class="evidence-card">
          <div class="evidence-head"><strong>${esc(e.source)}</strong><span class="access ${esc(e.visibility)}">${esc(e.visibility)}</span></div>
          <p>${esc(e.summary)}</p>
          <div class="evidence-meta"><span class="mini-tag">${esc(e.confidence)}</span>${e.observed_at?`<span class="mini-tag">${esc(e.observed_at)}</span>`:""}${e.rights?`<span class="mini-tag">${esc(e.rights)}</span>`:""}</div>
          <p class="${e.visibility==="public"?"":"redacted"}">${e.visibility==="public"?esc(e.locator||"No locator"): "Source locator withheld from public snapshot"}</p>
        </div>`).join("") || `<div class="empty-state">No public evidence records available.</div>`}
      </section>
      <section class="section"><h4>Disputes / uncertainty</h4>${bulletList(p.disputes)}</section>
      <section class="section"><h4>Data access</h4>${(p.data_resources||[]).map(d=>`<div class="evidence-card"><div class="evidence-head"><strong>${esc(d.title)}</strong><span class="access ${esc(d.visibility)}">${esc(d.access)}</span></div><p>${esc(d.notes||"")}</p><div class="evidence-meta">${d.license?`<span class="mini-tag">${esc(d.license)}</span>`:""}<span class="mini-tag">${esc(d.sensitivity||"none")}</span></div></div>`).join("") || `<div class="empty-state">No datasets attached.</div>`}</section>
    </div>
    <aside>
      <section class="section"><h4>Research frontier</h4>${bulletList(p.knowledge_frontier)}</section>
      <section class="section"><h4>System references</h4>${(p.system_refs||[]).map(r=>`<div class="review-card"><strong>${esc(r.system)}</strong><p>${esc(r.relation)} · ${esc(r.label||r.ref)}</p></div>`).join("") || `<div class="empty-state">No public cross-system references exposed.</div>`}</section>
      <section class="section"><h4>Rights / reuse</h4><p>${esc(p.rights_notes||"Source and data rights must be evaluated separately from code licensing.")}</p></section>
    </aside>
  </div>`;
}

function renderAttempts(p){
  const attempts = allAttemptsFor(p);
  return `<div class="two-col">
    <div>
      <section class="section"><h4>Attempts</h4>
        ${attempts.map(a=>`<div class="attempt-card"><div class="attempt-head"><div><strong>${esc(a.title||a.team)}</strong><small>${esc(a.team||a.contributor||"Contributor")} · ${esc(label(a.state||a.status))}</small></div><span class="mini-tag">${esc((a.focus||a.subproblem_ids||[]).toString())}</span></div><p>${esc(a.summary||a.notes||"Work attached to this problem.")}</p></div>`).join("") || `<div class="empty-state">No attempts recorded yet.</div>`}
      </section>
      <section class="section"><h4>Observed outcomes</h4>
        ${(p.outcomes||[]).map(o=>`<div class="outcome-card"><strong>${esc(o.summary)}</strong><p>${esc(o.observed_change)}</p><div class="evidence-meta"><span class="mini-tag">${esc(o.disposition||"observed")}</span><span class="mini-tag">attribution: ${esc(o.attribution||"not established")}</span><span class="mini-tag">${esc(o.date||o.observed_at||"")}</span></div></div>`).join("") || `<div class="empty-state">No real-world outcomes have been recorded. Prototype success is not impact.</div>`}
      </section>
    </div>
    <aside>
      <section class="section"><h4>Problem lifecycle</h4>${renderLifecycle(p)}</section>
      <section class="section"><h4>Living history</h4><div class="timeline">${(p.history||[]).map(h=>`<div><strong>${esc(h.label)}</strong><small>${esc(h.date)}${h.actor?` · ${esc(h.actor)}`:""}</small></div>`).join("")}</div></section>
      <section class="section"><button class="primary-button" data-action="attempt">Start a new attempt</button></section>
    </aside>
  </div>`;
}

function renderSteward(p){
  const checks = readinessChecks(p);
  return `<div class="two-col">
    <div>
      <section class="section"><p class="eyebrow">CURATION READINESS</p><h3>Publication is a reviewed transition, not a submit button.</h3>
        <div class="readiness-grid">${Object.entries(checks).map(([name,ok])=>`<div class="check ${ok?"ok":"no"}"><span>${esc(label(name))}</span><b>${ok?"✓":"×"}</b></div>`).join("")}</div>
      </section>
      <section class="section"><h4>Steward warnings</h4>${bulletList(stewardWarnings(p))}</section>
      <section class="section"><h4>Governance notes</h4><p>${esc(p.governance_notes||"Consequential action remains outside the commons until a competent owner/authority authorizes a bounded intervention.")}</p></section>
      <section class="section"><h4>Funding / stewardship</h4><p>${esc(p.funding_notes||"No funding metadata attached.")}</p></section>
    </div>
    <aside>
      <section class="section"><h4>Owner</h4><p>${esc(p.owner||"Unspecified")}</p></section>
      <section class="section"><h4>Sponsor</h4><p>${esc(p.sponsor||"None")}</p></section>
      <section class="section"><h4>Candidate intake</h4><p>${localCandidates().length} candidate(s) are stored locally in this browser demo. None are public.</p><button class="secondary-button" data-action="candidate">Add candidate</button></section>
      <section class="section"><h4>Next valid lifecycle moves</h4><p>${esc((p.next_states||[]).map(label).join(" · ")||"No transition metadata in demo packet.")}</p></section>
    </aside>
  </div>`;
}

function readinessChecks(p){
  return {
    observed_condition: !!p.observed_condition,
    unresolved_core: !!p.unresolved_core,
    reviewed_evidence: (p.evidence||[]).some(e=>["reviewed","corroborated","verified"].includes(e.confidence)),
    authority_boundary: !!p.authority,
    success_criteria: !!(p.success||[]).length,
    knowledge_frontier: !!(p.knowledge_frontier||[]).length,
    capability_frontier: !!(p.capabilities||[]).length,
    decomposition: !!(p.subproblems||[]).length,
    problem_owner: !!p.owner,
    implementation_pathway: !!(p.implementation_pathway||[]).length
  };
}
function stewardWarnings(p){
  const c = readinessChecks(p);
  const warnings = Object.entries(c).filter(([,ok])=>!ok).map(([name])=>`${label(name)} is incomplete.`);
  if((p.evidence||[]).some(e=>e.visibility!=="public")) warnings.push("Some source locators must remain redacted in public snapshots.");
  if(!(p.outcomes||[]).length) warnings.push("No real-world outcome yet; do not imply that the problem is solved.");
  return warnings.length ? warnings : ["No obvious V0.1 readiness gaps in this illustrative packet."];
}

function renderLifecycle(p){
  const order = ["candidate","researching","verified","open","piloting","deployed","monitoring","resolved"];
  const currentIndex = order.indexOf(p.status);
  return `<div class="lifecycle">${order.map((s,i)=>`<div class="life-step ${i<=currentIndex&&currentIndex>=0?"done":""}">${esc(label(s))}</div>`).join("")}</div>`;
}
function bulletList(items=[]){ return items.length ? `<ul>${items.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>` : `<div class="empty-state">Not yet established.</div>`; }

function bindDynamicActions(p){
  $$("[data-action='attempt']").forEach(btn=>btn.addEventListener("click",()=>openAttemptDialog(p,btn.dataset.subproblem)));
  $$("[data-action='research']").forEach(btn=>btn.addEventListener("click",()=>toast("Production flow: open a Cite workspace seeded with this packet's claims, evidence and unresolved frontier.")));
  $$("[data-action='capabilities']").forEach(btn=>btn.addEventListener("click",()=>toast("Production flow: query Refinery for validated reusable capabilities and known limitations.")));
  $$("[data-action='candidate']").forEach(btn=>btn.addEventListener("click",()=>$("#candidateDialog").showModal()));
  const match = $("#runMatch"); if(match) match.addEventListener("click",()=>runMatcher(p));
}

function runMatcher(p){
  const skills = $("#matchSkills").value.toLowerCase().split(",").map(x=>x.trim()).filter(Boolean);
  const interests = $("#matchInterests").value.toLowerCase().split(",").map(x=>x.trim()).filter(Boolean);
  const results = (p.subproblems||[]).map(s=>{
    const skillHits = (s.skills||[]).filter(x=>skills.some(q=>x.toLowerCase().includes(q)||q.includes(x.toLowerCase())));
    const interestHits = (s.interests||[]).filter(x=>interests.some(q=>x.toLowerCase().includes(q)||q.includes(x.toLowerCase())));
    return {s, score:skillHits.length*2+interestHits.length, skillHits, interestHits};
  }).sort((a,b)=>b.score-a.score);
  $("#matchResults").innerHTML = results.length ? results.slice(0,5).map(r=>`<button class="match-chip" data-jump="${esc(r.s.id)}"><strong>${r.score}</strong> ${esc(r.s.title)}${r.skillHits.length?` · ${esc(r.skillHits.join(", "))}`:""}</button>`).join("") : `<span class="match-chip">No open paths.</span>`;
  $$("[data-jump]").forEach(btn=>btn.addEventListener("click",()=>document.querySelector(`[data-subproblem="${CSS.escape(btn.dataset.jump)}"]`)?.scrollIntoView({behavior:"smooth",block:"center"})));
}

function openAttemptDialog(p, subproblemId){
  $("#attemptProblemId").value = p.id;
  $("#attemptSubproblem").innerHTML = (p.subproblems||[]).map(s=>`<option value="${esc(s.id)}" ${s.id===subproblemId?"selected":""}>${esc(s.kind)} — ${esc(s.title)}</option>`).join("");
  $("#attemptTitle").value = "";
  $("#attemptContributor").value = "";
  $("#attemptNotes").value = "";
  $("#attemptDialog").showModal();
}

function saveAttemptFromForm(e){
  e.preventDefault();
  const item = {
    id:`local-attempt:${crypto.randomUUID?.() || Date.now()}`,
    problem_id:$("#attemptProblemId").value,
    title:$("#attemptTitle").value.trim(),
    contributor:$("#attemptContributor").value.trim(),
    team:$("#attemptContributor").value.trim(),
    subproblem_ids:[$("#attemptSubproblem").value],
    focus:$("#attemptSubproblem").value,
    notes:$("#attemptNotes").value.trim(),
    state:"draft",
    created_at:new Date().toISOString()
  };
  if(!item.title || !item.contributor){ toast("Attempt title and contributor are required."); return; }
  const items=localAttempts(); items.push(item); saveLocal("pc-v01-attempts",items);
  $("#attemptDialog").close(); renderMetrics(); renderList(); if(currentProblem()?.id===item.problem_id){activeTab="attempts";renderDetail();activeTab="attempts";$$(".tab").forEach(x=>x.classList.toggle("active",x.dataset.tab==="attempts"));renderTab();}
  toast("Draft attempt created locally. Production workspaces would remain private by default.");
}

function saveCandidateFromForm(e){
  e.preventDefault();
  const candidate = {
    id:`local-candidate:${crypto.randomUUID?.() || Date.now()}`,
    title:$("#candidateTitle").value.trim(),
    observed_condition:$("#candidateCondition").value.trim(),
    geography:$("#candidatePlace").value.trim(),
    source:$("#candidateSource").value.trim(),
    status:"candidate",
    created_at:new Date().toISOString()
  };
  if(!candidate.title || !candidate.observed_condition){toast("Title and observed condition are required.");return;}
  const items=localCandidates(); items.push(candidate); saveLocal("pc-v01-candidates",items);
  $("#candidateDialog").close(); $("#candidateForm").reset();
  toast("Candidate saved locally. It is not public until curation gates are satisfied.");
  if(stewardMode && activeTab==="steward") renderTab();
}

function setStewardMode(next){
  stewardMode = next;
  document.body.classList.toggle("steward-mode",stewardMode);
  $("#stewardToggle").classList.toggle("active",stewardMode);
  $("#stewardToggle").textContent = stewardMode ? "Exit steward view" : "Steward view";
  if(!stewardMode && activeTab==="steward"){activeTab="overview";renderDetail();}
  else renderDetail();
}

async function boot(){
  const response = await fetch("problems.json");
  if(!response.ok) throw new Error(`Failed to load problems: ${response.status}`);
  problems = (await response.json()).filter(p=>PUBLIC_STATES.has(p.status));
  renderDomainFilter(); renderMetrics(); renderList();
  if(problems.length) selectProblem(problems[0].id);
}

$("#search").addEventListener("input",renderList);
$("#domainFilter").addEventListener("change",renderList);
$("#statusFilter").addEventListener("change",renderList);
$("#stewardToggle").addEventListener("click",()=>setStewardMode(!stewardMode));
$("#candidateButton").addEventListener("click",()=>$("#candidateDialog").showModal());
$("#heroCandidateButton").addEventListener("click",()=>$("#candidateDialog").showModal());
$("#saveAttempt").addEventListener("click",saveAttemptFromForm);
$("#saveCandidate").addEventListener("click",saveCandidateFromForm);

boot().catch(error=>{ $("#problemDetail").innerHTML=`<p>${esc(error.message)}</p>`; console.error(error); });
