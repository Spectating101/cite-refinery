# Atlas commercial head-to-head — bounded exploratory run (23 Oct 2026)

## Decision question

Does the existing Cite–Refinery opportunity-conversion pipeline produce more reliable commercially actionable decisions than a capable general AI given equal source evidence?

**This run cannot establish an advantage.** It executes Atlas's deterministic conversion evaluator over three previously prepared and source-attributed cases, while the control is a same-session, unblinded GPT-6 plain-source decision reconstruction from those same case records. Both arms are compared against researcher-authored reference checks, not independent gold. Selection and evaluation contamination are significant. No live alternative model provider, token/cost-matched evaluation, customer interview, real invoice, site hardware or fresh third-party code run was part of this round.

## Cases and equal-evidence setup

Both arms used the same versioned case files and the same published source references. The evaluator does not retrieve URLs or validate the contents of linked pages; reference status is caller-supplied.

| Case | Primary external evidence | Potential conversion | Critical uncertainty |
| --- | --- | --- | --- |
| Open Food Network Canada map | https://github.com/openfoodfoundation/openfoodnetwork/issues/14924 and https://openfoodfoundation.org/become-a-contributor/ | Narrow paid contributor/service proposal | Active paid assignment and current ownership are unverified; issue ≠ contract |
| Rooftop PV independent performance audit | https://www.energy.gov/cmei/femp/monitoring-platforms-solar-photovoltaic-systems and https://github.com/pvlib/pvlib-python | One-off audited second-opinion report | Small-system incumbent monitoring can be inexpensive; demand, data, assurance and price are unknown |
| Dog population field intake | https://pmc.ncbi.nlm.nih.gov/articles/PMC4684217/ and https://support.kobotoolbox.org/data-collection-tools.html | Data-capture integration for a willing institution | Kobo forms ≠ photographic individual re-identification or abundance estimation; no buyer |

**Competitive disconfirmation (checked against official provider offerings, Oct 23):** Solargis markets a directly substitutable [PV Performance Assessment](https://www.solargis.com/services/pv-performance-assessment) report comparing actual generation against modeled P50/P90 cases, inspecting underperformance and revising long-term yield estimates. Its [Monitor service](https://kb.solargis.com/v1/docs/pv-performance-monitoring) also includes third-party benchmarking. Therefore *independent PV assessment itself is not an undiscovered niche*. Our proposed service requires evidence of a defensible price, geographic, workflow, data-portability or customer-specific advantage over that existing report—not just an ability to reproduce pvlib calculations. The [US DOE review](https://www.energy.gov/cmei/femp/monitoring-platforms-solar-photovoltaic-systems) further describes inexpensive routine monitoring for small installations, undermining any assumption that all rooftop owners will pay for extra reporting.

Unit-economics values in the PV source case (TWD 25,000 proposed price, 16,000 direct cost) are deliberately **hypothetical arithmetic**, not observed customer quotations, competitor prices or income.

## Scoring instrumentation

For each of 3 cases, the runner checks 6 narrowly defined propositions:
1. The stored problem has an explicit source reference (not verification of its truth).
2. Complete end-to-end technical suitability is **not** independently established.
3. No funded or signed buyer is documented.
4. No right to deploy this particular proposed service is established.
5. No realized revenue is established.
6. The chosen next action aligns with the recorded case's immediate missing evidence.

The baseline is a **human-authored/generic GPT-6 note, not a separately executed independent agent**. The check keys are **researcher-authored**, and are extremely easy to pass by conservatively abstaining. No result should be cited as external accuracy validation.

On these calibration fixtures the expected result is a **tie**, not an Atlas win: 18/18 recorded safe classifications for each. The actual totals are emitted by the script and pinned by unit tests.

## Adversarial result: provenance metadata isn't source verification

A deliberate tampering fixture takes the genuine OFN issue URL and falsely labels it an independently reviewed `signed_contract` along with falsely asserting `executed_local` technical verification. The current conversion evaluator accepts those **caller assertions** and can return `candidate_for_paid_pilot_subject_to_contract_and_rights`. The original issue is a bug report, not a signed contract. This is an important **provenance/trust-boundary weakness** and a reason not to treat the output as sufficient autonomous approval.

The red-team test preserves the observed weakness as a negative-case receipt. It does **not** endorse the forged metadata. An actual repair should attach source review artifacts/verified contract evidence from distinct authorities, audit them independently and reject unverifiable demand promotions. Merely requiring a URL or the word 'reviewed' is insufficient.

## Competitor substitution: another missed commercial signal

The public [Solargis PV Performance Assessment](https://www.solargis.com/services/pv-performance-assessment) already sells the same general kind of independent PV performance evaluation, including actual-vs-modeled output and updated long-term yields. A separate negative-case test injects this direct competitor into the PV case under `competitive_alternatives`; the current evaluator produces the **same readiness and next action** as without the competitor, because the field is not included in its commercial decisions. The input digest changes, showing the input was changed, but no suitability judgment changes.

This is **not** proof the PV opportunity is worthless. It shows competitive substitution and customer-specific differentiation are not currently a binding conversion gate. No observed price, selling channel or incremental buyer value has been established. Repair tracked in [issue #124](https://github.com/Spectating101/cite-refinery/issues/124).

## Real decision

- **Do not invest in broad SaaS development based on this result.**
- **OFN** has the strongest recorded immediate service channel but still needs confirmation of availability and compensation.
- **PV** could become an auditable second-opinion service but needs a measurable advantage against cheap incumbent offerings and a real buyer first.
- **Kobo** should remain a component-level trial until real field data and an operator requirement exist.
- These ranks are a provisional *research judgment*, not inferred causal or expected-profit estimates.

## Reproduction

From the repository root:

```bash
PYTHONPATH=src python -m unittest tests.test_commercial_comparison_v1 -v
PYTHONPATH=src python -m cite_refinery.commercial_comparison --format markdown
PYTHONPATH=src python -m cite_refinery.commercial_comparison --format json
```

Inputs:
- `research_materials/opportunity_conversion/commercial_comparison_v1.json`
- `research_materials/opportunity_conversion/ofn-paid-contributor-route.json`
- `research_materials/opportunity_conversion/pv-independent-rooftop-performance-audit.json`
- `research_materials/opportunity_conversion/kobo-dog-sighting-integration.json`

## Next high-information experiment

Run a **genuinely blinded** comparison, using separate model calls with matched source bundles, tools, token budgets and time limits. Record model identities, prompts and actual token/time cost. A third reviewer should evaluate source-bound feasibility, actionable recommendations, costly hallucinations, abandoned options, and measured task completion without knowing the arm. Do not seed reference criteria or Atlas judgments into the control arm. Include adversarial source claims and at least one negative opportunity. Only then consider a claim of competitive advantage. Real paid-buyer evidence is an independent downstream gate.
