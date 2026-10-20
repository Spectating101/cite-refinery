# Cross-domain semantic evidence generalization — v1

20 October 2026. Experimental Cite-Refinery source-role and coverage validation; no accepted scientific claims.

## Purpose

Prove that source discovery, LLM semantic relevance, three-perspective knowledge mapping, and gap recovery function outside the dog-population case. Two unfamiliar topics were investigated without preselecting article URLs: **urban extreme-heat protection** and **informal e-waste exposure and worker protection**.

Each source is classified by what its actual passage says. Publisher identity is not proof of an implemented intervention or evaluated outcome. The system distinguishes practical problem observations, academic methods and findings, program guidance, documented implementation, and measured intervention effects. Off-topic pages add no coverage. Source IDs, module IDs, original passage fingerprints and verbatim source quotations are validated.

The separate Gemini High critic can only affirm, downgrade or exclude; it cannot upgrade a source's role. Both generator and reviewer are the same Gemini 3.8 Flash family and **not independent scientific adjudicators**. Only neutral source and module nodes enter the candidate graph, with explicit unresolved gaps. No cross-perspective causal links are automatically inferred.

## Actual two-domain live execution

**First search:** each domain returned 8 real retrieved records. For heat, four official-site pages were about unrelated waste, generic urban health, unrelated senior services and air pollution. For e-waste, the initial WHO hits mostly concerned UV exposure, caregiver training or generic healthcare waste. The model preserved those as off-topic rather than counting reputable websites as successful coverage.

**Gap-driven semantic recovery:** Gemini selected new searches without a curated paper list, discovering 6 additional urban-heat leads and 7 additional e-waste leads. A bounded combined source ledger of up to 12 records per domain was reclassified and critically reviewed.

### Urban heat

- **Practical**: WHO heat-health sources document heat exposure, risks from inadequate housing and limited cooling access for vulnerable communities.
- **Academic**: Research literature reports temperature-health associations and vulnerability mechanisms.
- **Program**: Actual WHO material supports heat action-plan and warning-system **guidance**.
- **Not established:** a specific locally deployed cooling-center/alert scheme reducing observed human morbidity or mortality, or independent replication.

### Informal e-waste

- **Practical**: the role-specific local direct observation layer remains insufficient even though adjacent source material mentions e-waste hazards.
- **Academic**: focused e-waste study methods and reported findings appear.
- **Program**: WHO e-waste guidance plus a quasi-randomized Thai safer-tools intervention (DOI: https://doi.org/10.5271/sjweh.4259) provide material for distinct program roles. The paper reports reduced **self-reported occupational injuries** over three months. It does **not** demonstrate reduced blood lead, heavy metals or toxicant exposures.
- **Not established:** independent field replication or population-level reduction in toxicant burden.

| Perspective | Urban heat | Informal e-waste |
|---|---|---|
| Practical | Direct source coverage | Remains a source-role gap |
| Academic | Direct research coverage | Direct methods/finding coverage |
| Program | Guidance, no evaluated outcome | Guidance and measured workplace injury intervention |
| Independent field replication | None | None |

### Actual graph receipts

- Heat: 13 neutral nodes / 16 candidate-or-unresolved relationships; sgpacket:4643fdf4902854d5.
- E-waste: 10 neutral nodes / 9 candidate-or-unresolved relationships; sgpacket:842509edad9e482f.

Nothing was merged, deployed or elevated to authoritative evidence. Existing parallel worktrees and the previous dog investigation workspace were not modified.

## Implementation and reproduction

- cross_domain_roles.py: semantic source role classification, exact source quote verification and perspective-specific coverage requirements.
- cross_domain_role_critic.py: separate downgradable critic contract and uncertainty preservation.
- cross_domain_recovery.py: model-planned searches targeting actual coverage holes, not manually supplied publisher URLs.
- cross_domain_graph.py: neutral source-module-gaps graph and idempotent/stage safety check.
- cross_domain_probe_cli.py: checkpointed source discovery, model and critic execution, recovery and graph staging.
- The seed module ontology and sanitized reports are in research_materials/runtime_trials/cross_domain_20261020.

Run the installed command cite-refinery-cross-domain-probe with the seed JSON, one of urban_heat or ewaste_exposure, an isolated workspace and output directory, followed by the steps:

1. init
2. plan
3. collect
4. roles
5. critic
6. recover
7. --include-recovery roles
8. --include-recovery critic
9. --include-recovery graph
10. status

Gemini via Antigravity is an explicit provider for this trial; the normal investigator still defaults to the user's registered GitHub Copilot backend.

## Boundaries

These two domains demonstrate portability of **semantic evidence roles and source recovery**, not measured accuracy for a complete general-purpose knowledge graph. No human-labeled holdout, independent model-family consensus, cross-domain contradiction adjudication or replicated empirical intervention effect was established. The source search backend still returns off-topic institutional results; these must be evaluated by passage content and recovered or left as gaps.

The next important gate is to benchmark false program-outcome attribution on independently annotated examples drawn across many domains, and then generalize topic-module discovery rather than assuming three predefined modules comprehensively map a field.
