# Problem Commons V0.1 browser prototype

This directory is the public-facing prototype for the broader **Problem Commons** concept.

It is deliberately problem-first. The public user sees living problem objects and contribution paths; Nocturnal, Public-Good, Cite, Refinery, and Citation Engine remain supporting systems behind those objects.

## Run locally

From this directory:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080`.

Do not open `index.html` directly with `file://`; the browser blocks `fetch("problems.json")` in many configurations.

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

## Public vs steward surfaces

Anonymous/public users should normally see only `verified`, `open`, `partially_resolved`, `piloting`, `deployed`, `monitoring`, and `resolved` packets. Candidate/researching/reframed/retired/invalidated state remains curator-side by default.

Toggle **Steward view** in the prototype to inspect readiness checks, owner/authority gaps, candidate intake, and governance warnings.

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
