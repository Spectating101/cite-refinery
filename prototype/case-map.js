const PUBLIC_STATES = new Set(["verified","open","partially_resolved","piloting","deployed","monitoring","resolved"]);
const DEPLOYED_STATES = new Set(["deployed","monitoring","resolved"]);
const REQUIRED_DEPLOY_GATES = ["evidence","safety","integrity","rights","data-access","reversibility","authority"];
const MILESTONES = [
  ["formulated","Problem formulated"],
  ["public","Problem public"],
  ["decomposed","Work decomposed"],
  ["staged","Work staged"],
  ["attempted","Attempt started"],
  ["accepted","Attempt accepted"],
  ["governed","Intervention governed"],
  ["tested","Test recorded"],
  ["authorized","Authority recorded"],
  ["deployed","Deployed"],
  ["outcome","Outcome observed"],
  ["reuse","Reuse observed"]
];

let problems = [];
let stageProfiles = [];
let governanceEnvelopes = [];

const $ = (id) => document.getElementById(id);
const esc = (value = "") => String(value).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c]));

async function load() {
  const [p, s, g] = await Promise.all([
    fetch("problems.json").then(r => r.json()),
    fetch("stage-profiles.json").then(r => r.json()),
    fetch("governance-envelopes.json").then(r => r.json())
  ]);
  problems = Array.isArray(p) ? p : (p.problems || []);
  stageProfiles = s.profiles || [];
  governanceEnvelopes = g.envelopes || [];
  const select = $("problemSelect");
  problems.forEach(problem => {
    const option = document.createElement("option");
    option.value = problem.id;
    option.textContent = `${problem.title} · ${problem.status}`;
    select.appendChild(option);
  });
  select.addEventListener("change", render);
  render();
}

function caseData(problem) {
  const subproblems = problem.subproblems || [];
  const stages = stageProfiles.filter(x => x.problem_id === problem.id);
  const envelopes = governanceEnvelopes.filter(x => x.problem_id === problem.id);
  const attempts = problem.attempts || [];
  const outcomes = problem.outcomes || [];
  const accepted = attempts.filter(x => ["accepted","completed"].includes(x.state || x.status));
  const tests = envelopes.flatMap(x => x.tests || []);
  const handoffs = envelopes.flatMap(x => x.handoffs || []);
  const authority = handoffs.some(x => x.decision === "authorized") || (problem.authority_decisions || []).some(x => x.decision === "authorized");
  const formulated = Boolean(problem.unresolved_core && problem.authority && (problem.evidence || []).length && (problem.success || problem.success_criteria || []).length);
  const stagedIds = new Set(stages.map(x => x.subproblem_id));
  const staged = subproblems.length > 0 && subproblems.every(x => stagedIds.has(x.id));
  const milestones = {
    formulated,
    public: PUBLIC_STATES.has(problem.status),
    decomposed: subproblems.length > 0,
    staged,
    attempted: attempts.length > 0,
    accepted: accepted.length > 0,
    governed: envelopes.length > 0,
    tested: tests.length > 0,
    authorized: authority,
    deployed: DEPLOYED_STATES.has(problem.status),
    outcome: outcomes.length > 0,
    reuse: false
  };
  return {subproblems, stages, envelopes, attempts, outcomes, accepted, tests, handoffs, milestones};
}

function governanceBlockers(envelope) {
  const blockers = [];
  const gates = new Map((envelope.gates || []).map(g => [g.kind, g]));
  REQUIRED_DEPLOY_GATES.forEach(kind => {
    const gate = gates.get(kind);
    if (!gate) blockers.push(`missing ${kind} gate`);
    else if (gate.status !== "satisfied" && gate.status !== "not-applicable") blockers.push(`${kind} gate ${gate.status}`);
  });
  const professional = gates.get("professional");
  if (professional && !["satisfied","not-applicable"].includes(professional.status)) blockers.push(`professional gate ${professional.status}`);
  if (!(envelope.tests || []).some(t => t.passed && !(t.guardrail_breaches || []).length)) blockers.push("no passed guardrail-safe test receipt");
  if (!(envelope.handoffs || []).some(h => h.decision === "authorized") && !(envelope.authority_actor || "").trim()) blockers.push("no external authority receipt");
  return blockers;
}

function deriveNext(problem, data) {
  const actions = [];
  const blockers = [];
  const warnings = [...(problem.disputes || problem.disputes_uncertainty || [])];
  const stagedIds = new Set(data.stages.map(x => x.subproblem_id));
  const unstaged = data.subproblems.filter(x => !stagedIds.has(x.id));

  if (!data.milestones.formulated) actions.push("Complete evidence-bounded problem formulation before treating this as a mature public problem.");
  if (unstaged.length) actions.push(`Classify ${unstaged.length} remaining contribution path(s) by work stage and epistemic mode.`);
  if (PUBLIC_STATES.has(problem.status) && !data.attempts.length) actions.push("Match or recruit an independent solver and start a bounded attempt on one explicit contribution path.");
  const submitted = data.attempts.filter(x => (x.state || x.status) === "submitted");
  if (submitted.length) actions.push(`Review ${submitted.length} submitted attempt(s) independently.`);
  if (data.accepted.length && ["open","partially_resolved"].includes(problem.status)) actions.push("Decide whether accepted work justifies a bounded shadow/pilot transition; do not infer impact from acceptance.");

  data.envelopes.forEach(env => {
    const envBlockers = governanceBlockers(env);
    if (!(env.tests || []).length) {
      const nonAuthority = envBlockers.filter(x => !x.includes("authority") && !x.includes("passed guardrail"));
      if (!nonAuthority.length) actions.push(`Run a bounded test for “${env.title}” and record its evaluation receipt.`);
    }
    envBlockers.forEach(b => blockers.push(`${env.subproblem_id}: ${b}`));
  });

  if (DEPLOYED_STATES.has(problem.status) && !data.outcomes.length) actions.push("Monitor the real external condition and record outcome evidence separately from activity receipts.");
  if (data.outcomes.length) actions.push("Identify generalizable evidence/method/capability and test whether a later problem can reuse it at positive net benefit.");
  if (!actions.length) actions.push("Continue longitudinal monitoring and look for a defensible cross-problem reuse opportunity.");
  if (!data.milestones.reuse) warnings.push("Browser prototype does not contain the pilot reuse ledger; reuse remains unproven here even if capabilities exist.");
  return {actions:[...new Set(actions)], blockers:[...new Set(blockers)], warnings:[...new Set(warnings)]};
}

function render() {
  const problem = problems.find(x => x.id === $("problemSelect").value) || problems[0];
  if (!problem) return;
  $("problemSelect").value = problem.id;
  const data = caseData(problem);
  const derived = deriveNext(problem, data);
  $("caseState").textContent = `${problem.status} · ${Object.values(data.milestones).filter(Boolean).length}/${MILESTONES.length} milestones`;

  $("milestones").innerHTML = MILESTONES.map(([key,label]) => `
    <div class="milestone ${data.milestones[key] ? "done" : ""}">
      <b>${esc(label)}</b><span>${data.milestones[key] ? "record present" : key === "reuse" ? "pilot ledger needed" : "not yet evidenced"}</span>
    </div>`).join("");

  $("caseHeader").innerHTML = `
    <div class="eyebrow">${esc(problem.domain)} · ${esc(problem.geography || "scope unspecified")}</div>
    <h2>${esc(problem.title)}</h2>
    <p class="small">${esc(problem.unresolved_core || problem.summary || "")}</p>
    <div class="meta"><span class="pill">${esc(problem.status)}</span><span class="pill">owner: ${esc(problem.owner || problem.problem_owner || "unspecified")}</span><span class="pill">authority: ${esc(problem.authority || problem.authority_boundary || "unspecified")}</span></div>`;

  const stageRate = data.subproblems.length ? Math.round((data.stages.length / data.subproblems.length) * 100) : 0;
  $("caseMetrics").innerHTML = [
    [data.subproblems.length,"contribution paths"],
    [`${stageRate}%`,"stage coverage"],
    [data.envelopes.length,"governance envelopes"],
    [data.outcomes.length,"observed outcomes"]
  ].map(([value,label]) => `<div class="metric"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`).join("");

  const bySub = new Map(data.stages.map(x => [x.subproblem_id, x]));
  $("stageRows").innerHTML = data.subproblems.length ? data.subproblems.map(sub => {
    const stage = bySub.get(sub.id);
    return `<div class="row"><strong>${esc(sub.title)}</strong><p>${esc(sub.detail || sub.description || "")}</p><div class="state">${stage ? `<span>${esc(stage.stage)}</span><span>${esc(stage.work_mode || stage.epistemic_type)}</span><span>${esc(stage.uncertainty)} uncertainty</span>` : `<span>unstaged</span>`}</div></div>`;
  }).join("") : `<div class="empty">No contribution decomposition recorded.</div>`;

  $("governanceRows").innerHTML = data.envelopes.length ? data.envelopes.map(env => {
    const b = governanceBlockers(env);
    const satisfied = (env.gates || []).filter(g => ["satisfied","not-applicable"].includes(g.status)).length;
    return `<div class="row"><strong>${esc(env.title)}</strong><p>${esc(env.smallest_feasible_change || "")}</p><div class="state"><span>${satisfied}/${(env.gates || []).length} gates satisfied</span><span>${(env.tests || []).length} tests</span><span>${b.length ? `${b.length} deploy blockers` : "deploy-ready"}</span></div></div>`;
  }).join("") : `<div class="empty">No concrete intervention envelope. This can be appropriate for observation/research-only work.</div>`;

  const attemptRows = data.attempts.map(a => `<div class="row"><strong>Attempt · ${esc(a.title || a.id)}</strong><p>${esc(a.summary || a.notes || "")}</p><div class="state"><span>${esc(a.state || a.status || "unknown")}</span></div></div>`);
  const outcomeRows = data.outcomes.map(o => `<div class="row"><strong>Outcome · ${esc(o.summary || "Observed change")}</strong><p>${esc(o.observed_change || o.change || "")}</p><div class="state"><span>${esc(o.attribution || "attribution not established")}</span></div></div>`);
  $("attemptOutcomeRows").innerHTML = [...attemptRows,...outcomeRows].join("") || `<div class="empty">No attempts or observed outcomes recorded in this illustrative packet.</div>`;

  $("nextActions").innerHTML = derived.actions.map(x => `<div class="action">${esc(x)}</div>`).join("");
  $("blockers").innerHTML = derived.blockers.length ? derived.blockers.map(x => `<div class="blocker">${esc(x)}</div>`).join("") : `<div class="good">No derived governance blocker in this static view.</div>`;
  $("warnings").innerHTML = derived.warnings.length ? derived.warnings.map(x => `<div class="warning">${esc(x)}</div>`).join("") : `<div class="good">No additional warning.</div>`;
}

load().catch(err => {
  document.body.innerHTML = `<main class="shell"><div class="panel"><h2>Case view failed to load</h2><pre>${esc(err.message)}</pre></div></main>`;
});
