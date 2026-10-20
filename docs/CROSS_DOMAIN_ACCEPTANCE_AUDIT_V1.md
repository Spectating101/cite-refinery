# Cross-domain acceptance audit — urban heat and e-waste

2026-10-20. Source-artifact analysis, not independent scientific validation.

The existing cross-domain probe had already tested **urban heat** and **informal e-waste exposure**. This branch does not repeat those model calls or change the other agent's checkout. It validates the saved source-role and coverage artifacts in a separate Git worktree.

## Recovered source role coverage

| Domain | Practical | Academic | Program |
|---|---|---|---|
| Urban extreme heat | Recovered direct source | Direct research coverage | Guidance only; no measured local health impact |
| Informal e-waste | Still missing direct practical evidence role | Direct research coverage | Guidance plus workplace injury intervention outcome |

Recovery improved the practical layer for heat and the program layer for e-waste. It did **not** fill the e-waste practical gap or verify independent field replication.

## Critical endpoint qualification

The e-waste intervention reports **reduced self-reported injuries** over three months. It does **not** establish reduced blood lead, toxicant burdens, or community illness. This audit explicitly records the endpoint as self-reported workplace injury, and blocks silent conversion to a biomarker benefit. An unclassifiable endpoint remains explicitly unknown.

## Checks

- Source IDs are unique and declared direct coverage matches critically reviewed rows.
- Measured program outcomes require a directly attributed reviewed program-outcome source.
- Claims of independently validated implementation or independent field replication fail closed.
- Recovered gaps are preserved rather than assumed resolved.
- A deterministic JSON acceptance report can be recreated without any LLM calls.

Files: src/cite_refinery/cross_domain_acceptance.py, tests/test_cross_domain_acceptance_v1.py, and research_materials/runtime_trials/cross_domain_20261020/independent_acceptance_audit.json.

**Scope:** This is an independent engineering consistency audit over previously generated model reviews, NOT independent annotation of the source text or measured broad semantic accuracy. Same-family Gemini critique does not provide external validation. No source was auto-promoted, no repository was merged or deployed, no new evidence was invented.

## Next real validation gate

An externally adjudicated multi-domain held-out set should measure program-outcome false promotion, role-specific precision and recall, and the difference between practical problems, academic findings and program outcomes. Additional modules must be discovered and tested instead of presuming six seed modules represent the landscape.
