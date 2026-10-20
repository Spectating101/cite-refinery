# Cross-layer interpretation — substantive findings (v1)
20 October 2026. Draft child of PR #71. The 232-source corpus and sealed 66-source holdout are unchanged.

## Product behavior
**Practical observation → academic mechanism/method → program implementation → mismatch and limitation → next action.**

The new cross-layer stack produces investigator findings rather than just three categorized source lists.

### Path 1 — source-reviewed semantic graph
SemanticGraph.cross_layer_dossier(project_id) interprets persisted nodes and qualified relationships scoped to exactly one project. stack_packet(packet) does the same for a review packet without persistence. It follows relation identities and statuses, **not word similarity or same-cluster membership**. It supports practical measurement qualifications, implementation-method mismatches and missing program evaluation *within the reviewed graph*. Every finding includes a chain of edges and source references. Candidate or unresolved links do not become accepted claims.

### Path 2 — previously unclassified source materials
cross_layer_proposals uses already mapped development-only source readings, groups them by their candidate source roles, and asks an authenticated AI model to propose mechanisms, implementation fits, counterarguments, scope mismatches and next tests. It must leave perspectives empty when source support is absent. With an optional authorized development-only local original corpus, every source ID, SHA-256 fingerprint and exact quoted passage is checked. Quotation correctness still does not establish semantic entailment or causal impact.

## Real results

### Taiwan roaming dogs — reviewed case
- The government says the decline from its 2022 to 2024 population estimate was not statistically significant; the system retains that qualification rather than claiming an intervention worked.
- The methodological chain says repeated individual-aware observations require reliable individual reconciliation. Talea documents roaming-dog sightings but its user guide does not document a photo field for a sighting. The engine traces a review-qualified LIMITED_BY / MISSING_LINK chain to the unmet methodological requirement.
- **Useful next test:** determine whether individual identification can be done reliably via a separate system or another method before claiming a continuous estimator. The engine does **not** say Talea itself is useless.
- Another joined thread links Miaoli replenishment reports, Shoushan open-population modeling and Taiwan's policy response; it leaves intervention effectiveness unevaluated within the reviewed material.

This is a meaningful **automatic interpretation of a curated graph**. The original relationships were manually source-reviewed, so it is not proof of autonomous discovery.

### Food surplus redistribution — previously unclassified evidence atlas
- A candidate Practical + Academic interpretation connects field observations and reviews of social supermarkets: short-term access is plausible, while dependence on ongoing commercial surplus and limited evidence on long-term nutritional/economic outcomes remain concerns. The decisive follow-up would directly measure beneficiary dietary and economic outcomes.
- A candidate Academic + Program interpretation links a food-donation lifecycle assessment with a separately published IoT rescue pilot that **reports** 847 kg redistributed and 42% faster collection. Those reported pilot metrics are outputs, not proof of improved recipient nutrition, end-to-end audited environmental benefits or profitable operations.
- Two distinct partial links were found, **not a fully supported single three-perspective connection**. The model did not fabricate the missing perspective just to fill a chart.
- A second live model run using SHA-matched original development texts generated source quotations for each selected record. We caught its statement that the pilot directly implements an unrelated LCA hypothesis; an explicit guard now rejects that unproven direct cross-source linkage. The correct interpretation is *potentially relevant approach*, not validation of the separate study.

### Flood preparedness — previously unclassified evidence atlas
- One candidate Academic + Program comparison links Uganda research on flood severity to a Laos early warning and local response case. Applicability across geographies is unresolved; deployment activities do not establish causal mortality benefit.
- One candidate **three-perspective** connection joins Practical observations of flood-associated health-system pressure in Pakistan, Academic multi-hazard flood-risk research, and Program guidance from WHO/Europe.
- The system points out that European guidance is **not evidence that comparable policies were implemented or improved outcomes in Pakistan**. A proper next test would evaluate actual local preparedness rollouts and health continuity/disease outcomes.
- This run used earlier model-produced source readings, not a second independent source-level verification pass. It remains a plausible candidate, not an accepted field conclusion.

## Limitations that remain

These tests do NOT establish autonomous discovery novelty, scientific claim accuracy, causal identification, independent human performance gains or economic value. Exact quotes can be true while the derived cross-source inference is wrong. A missing role in selected sources does not mean no suitable evidence exists globally. Do not count a graph's complete three-layer structure as proof of a real-world intervention's effectiveness.

The implementation is intentionally read-only, supports source-status review, and does not merge any graph edges or alter frozen evaluation material.

## Reproduction

From the repository, one can call:

- graph.cross_layer_dossier(project_id) — real project-scoped graph stack
- python -m cite_refinery.cross_layer_cli packet PATH_TO_REVIEWED_PACKET
- python -m cite_refinery.cross_layer_cli atlas PROVISIONAL_MAP GLOBAL_ATLAS --domain "EXACT DOMAIN" --provider antigravity --model gemini-3.8-flash-medium
- Add --source-corpus PATH_TO_AUTHORIZED_LOCAL_DEVELOPMENT_CORPUS to check the original source text and demand exact matched quotes.
- To replay a previous answer without model execution, supply --model-output RESPONSE_JSON.
- --output PATH and --format markdown are CLI top-level options placed before the subcommand.

The independently source-reviewed Taiwan case dossier is saved in the runtime-trials folder. Complete original-source material and source-quote-bearing experimental results remain private on Optiplex.

## Advancement gate

Now test researcher-facing findings against an equivalent general assistant using the same materials, then independently adjudicate whether the cited evidence actually entails the problem-solution relationship. Expand models and features only if the **quality of discoveries** demonstrably improves.
