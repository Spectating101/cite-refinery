# Problem Commons V0.1 browser prototype

This directory is the public-facing prototype for the broader **Problem Commons** concept.

It is deliberately problem-first. The public user sees living problem objects and contribution paths; Nocturnal, Public-Good, Cite, Refinery, and Citation Engine remain supporting systems behind those objects.

## Run locally

From this directory:

```bash
python -m http.server 8080
```

Then open:

- `http://localhost:8080/` — the living Problem Commons browser.
- `http://localhost:8080/case-map.html` — the **end-to-end Case view** joining Problem Packet, stages, governance, attempts and outcomes into a derived milestone/blocker view.
- `http://localhost:8080/stage-map.html` — the experimental **Observe → Measure → Explain → Design → Build → Test → Deploy → Monitor → Generalize** contribution map.
- `http://localhost:8080/governance-map.html` — the **Public-Good governance bridge** showing intervention hypotheses, hard gates, test readiness, deployment blockers, and external-authority handoff state.
- `http://localhost:8080/review.html` — the **external pilot review surface** for loading a minimum-necessary owner/reviewer/solver review pack, completing the fixed rubric, and returning a completed response JSON without exposing internal state.

Do not open the main data-backed pages directly with `file://`; the browser blocks local `fetch(...)` in many configurations. The external review page reads only a user-selected local JSON pack and does not fetch restricted evidence.

## What V0.1 demonstrates

- public catalog restricted to verified/public lifecycle states;
- full living Problem Packet detail rather than a static challenge brief;
- observed condition vs unresolved core vs working diagnosis;
- knowledge frontier and reusable capability frontier;
- measurable success/falsification plus guardrails;
- explicit authority and implementation pathway;
- evidence/data visibility and public redaction cues;
- contribution decomposition by research/data/domain/engineering/design/validation;
- deterministic skill/interest matching;
- explicit credential gates only where a contribution path genuinely requires them;
- browser-local draft attempts;
- browser-local problem-candidate intake that does **not** publish directly;
- attempts separated from outcomes;
- lifecycle and recurrence framing;
- steward-only readiness checks and curation warnings;
- safe external owner/reviewer/solver review packs and a browser surface for completing them.

The five bundled public packets are **illustrative**. They exercise different lifecycle states and domains; they are not claims about current real-world conditions. Real-source pilot candidates remain under `pilot/` and are explicitly non-public until their curation gates pass.

## End-to-end Case view

`case-map.html` is the browser counterpart of the backend `ProblemCaseWorkspace` / `problem-case` CLI.

It joins the current illustrative Problem Packet, stage profiles and governance envelopes and shows a derived milestone rail:

1. problem formulated;
2. problem public;
3. work decomposed;
4. work staged;
5. attempt started;
6. attempt accepted;
7. intervention governed;
8. test recorded;
9. authority recorded;
10. deployed;
11. outcome observed;
12. reuse observed.

It also surfaces:

- stage coverage across contribution paths;
- governance envelopes and deploy blockers;
- attempts and observed outcomes;
- the next bounded action;
- unresolved evidence / interpretation warnings.

This view is **derived**. It cannot grant authority or create evidence. The static browser does not contain the pilot reuse ledger, so it must not claim reuse merely because a reusable-looking capability exists.

The authoritative operator/reviewer bundle is produced by the backend `problem-case export` command; see `docs/PROBLEM_CASE_WORKSPACE.md`.

## External pilot review surface

`review.html` is intentionally separate from the steward/operator surfaces.

The curator first creates a minimum-necessary pack:

```bash
problem-case review-pack problem:... --audience owner --out /tmp/owner.json
problem-case review-pack problem:... --audience reviewer --out /tmp/reviewer.json
problem-case review-pack problem:... --audience solver --out /tmp/solver.json
```

The participant loads that JSON into `review.html`. The page renders only the redacted/public projection plus safe stage/governance context and captures the fixed rubric.

Owner/reviewer responses can record:

- material disagreements and factual/formulation errors;
- whether reframing is required;
- a non-binding publication recommendation;
- review notes.

Solver responses can additionally record:

- selected contribution path;
- minutes to a useful contribution edge;
- usefulness rating;
- serious-attempt conversion;
- abandonment and reason;
- observer notes.

The page never submits or promotes anything automatically. It produces a completed JSON pack that a curator explicitly ingests through:

```bash
problem-ops review-ingest /tmp/completed-review.json --participant participant-id
```

Review scores remain pilot measurements. They do not become publication, professional authority, institutional authority, successful tests, or outcomes.

## Experimental problem-solving stage map

`stage-map.html` pressure-tests a new V0.1 extension rather than changing the canonical Problem Packet schema prematurely.

Each selected contribution path is classified by:

- problem-solving stage;
- epistemic type;
- uncertainty;
- method maturity;
- expected output;
- evaluation method;
- professional/institutional authority requirement;
- default system routes;
- reuse target.

The prototype derives four work modes:

- **known practice** — established method, low uncertainty;
- **adaptive practice** — known/adaptable method fitted to context;
- **empirical inquiry** — trustworthy new evidence is required;
- **research frontier** — method or knowledge itself is novel/frontier.

Professional authority is intentionally separate from this scale. A licensed practitioner can be required for low-uncertainty work; academic research skill does not confer professional or institutional authority.

The stage view is backed by `stage-profiles.json`, mirrored from `../examples/problem_stage_profiles.json`. It is an empirical hypothesis: if it adds ceremony without improving solver comprehension, matching, handoffs, or reuse capture, it should remain internal or be removed rather than becoming mandatory schema.

## Public-Good governance bridge

`governance-map.html` visualizes `problem-governance/v0.1` intervention envelopes.

The stage map answers **what kind of work is this?** The governance map answers **can this proposed intervention responsibly move from Design → Test → Deploy?**

Each envelope exposes:

- target failing transition and diagnosis hypothesis;
- intervention class and smallest feasible change;
- expected mechanism;
- reversibility and rollback plan;
- evidence, safety, integrity, rights, data-access and professional gates;
- outcome metrics and monitoring plan;
- test receipts;
- explicit external-authority state.

The browser intentionally shows examples that are review/test-ready while still deployment-blocked. A successful build or even a successful test does not become permission to act. Real deployment remains outside Problem Commons under competent external authority.

The browser data in `governance-envelopes.json` is mirrored from `../examples/problem_governance_envelopes.json`; CI rejects drift between them.

## Real-source candidate admission

A standalone researched draft can enter the live pilot registry through the fail-closed operations path:

```bash
problem-ops draft-import pilot/drafts/taoyuan-mobility.candidate.v0.1.json --actor pilot-curator
```

Draft admission accepts only `candidate`, `researching`, or `reframed` non-public packets. It rejects embedded attempts, authority decisions, outcomes, public visibility, and advanced/public lifecycle states. Possible duplicates must be reviewed or explicitly overridden.

The included Taoyuan mobility draft therefore enters as `researching/restricted`; it does **not** become a published pedestrian-safety claim. Its metadata-only evidence, missing owner/domain review, unresolved joinability/exposure, and competing mechanisms remain visible blockers.

## Public vs steward surfaces

Anonymous/public users should normally see only `verified`, `open`, `partially_resolved`, `piloting`, `deployed`, `monitoring`, and `resolved` packets. Candidate/researching/reframed/retired/invalidated state remains curator-side by default.

Toggle **Steward view** in the main prototype to inspect readiness checks, owner/authority gaps, candidate intake, and governance warnings.

## Production boundary

The browser currently uses local JSON and `localStorage` for demo attempts/candidates. Production should use the V0.1 kernel/API with:

- private-by-default registered workspaces;
- verified partner access for restricted evidence/data;
- sandboxed/allow-listed execution;
- explicit publication review;
- role-separated operator/reviewer/steward permissions;
- public redaction/minimum-necessary exports;
- competent human/institutional authority for consequential action.

The prototype intentionally does not implement arbitrary public code execution or autonomous intervention.
