# Canonical investigation entry — minimal integration

October 21, 2026. Draft child of reconciliation PR #86.

This is **interface integration**, not a new research engine or proof of end-to-end, three-layer operation.

## What changed

The canonical command now delegates to the existing durable InvestigationController:

    cite-refinery investigate --workspace /tmp/example-investigations init --question "How do positive feedstock fees affect battery recycling viability?"

    cite-refinery investigate --workspace /tmp/example-investigations status --id SESSION_ID

The legacy cite-refinery-investigate executable remains compatible, including the existing reviewed --modules ontology input.

For a new question without --modules, the CLI creates one provisional RQ-01 module directly from the user's own wording. It is tagged user_question_provisional and unreviewed. This framing is NOT evidence that the practical problem has been measured, that science supports any intervention or that an implementation works. Init and status do not invoke models or networks.

The new CLI summary explicitly reports candidate_neutral_only authority, the provisional module origin, unverified practical field-data and implementation outcome source families, and that end_to_end_three_layer_validation_complete is false.

## Tested breadth, not yet general end-to-end performance

The exact same command initializes and persists previously unseen questions about battery recycling costs, classroom CO2 monitoring and cooperative invoice quantity conversions. Tests also confirm existing ontology inputs and the old command still function. These are three successful setup/status flows, **not** three completed research investigations or validated solutions.

The existing controller currently searches academic abstracts and institutional sources and stages candidate-only evidence. It lacks general independent practical observations and verified implementation/operation acquisition for an arbitrary question. Do not claim complete Practical, Academic, Implementation knowledge mapping from two source families.

## Next proof

Add a generic source-input contract for supplied practical observations and implementation candidates within the existing controller, with strict provenance and abstention rules. Test multiple domains and negative cases without new case-specific modules, then consolidate duplicate entrypoints after dependency analysis. Commercial viability and real operator demand remain separate validation tasks.

No external changes or graph status promotions are performed by initiation.
