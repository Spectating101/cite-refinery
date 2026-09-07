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
- `http://localhost:8080/stage-map.html` — the experimental **Observe → Measure → Explain → Design → Build → Test → Deploy → Monitor → Generalize** contribution map.

Do not open the pages directly with `file://`; the browser blocks local `fetch(...)` in many configurations.

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
- steward-only readiness checks and curation warnings.

The five bundled packets are **illustrative**. They exercise different lifecycle states and domains; they are not claims about current real-world conditions.

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
