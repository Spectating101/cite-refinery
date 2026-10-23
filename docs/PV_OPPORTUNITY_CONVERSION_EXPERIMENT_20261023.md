# Opportunity conversion experiment: independent rooftop PV audit (2026-10-23)

This is a **new, source-backed case fed to the existing Cite–Refinery opportunity-conversion evaluator**. It is not a customer pilot, a site performance validation, or proof of Atlas discovering an opportunity autonomously. The researcher selected the lead and reviewed the source material; the evaluator tests whether evidence and rights constraints survive conversion.

## Three-layer investigation

**Practical:** Operating rooftop PV systems need data-quality controls, production benchmarking, fault triage and trustworthy performance reports. The US Department of Energy describes numerous established monitoring alternatives, including independent third-party services. This is a *known operational use case*, not proof of an unmet or funded Taiwanese customer need.

- https://www.energy.gov/cmei/femp/monitoring-platforms-solar-photovoltaic-systems

**Academic:** A 2025 review of distributed PV fault diagnosis documents constraints around data availability and real-world validation. A 2026 review of low-cost monitoring identifies uncertainty, lifecycle and cost-effectiveness shortcomings in many published architectures. Neither asserts that our proposed service is unique.

- https://doi.org/10.1016/j.apenergy.2025.126636
- https://doi.org/10.1016/j.rser.2025.116417
- A 2025 rooftop-PV case study demonstrates monitored-data assessment at a 1.05 MW university installation: https://doi.org/10.1016/j.renene.2024.121947

**Program / available supply:** pvlib-python supports PV modeling and publishes a BSD-3-Clause license, subject to compliance review. PVAnalytics is a further data quality tool, not a source of demand. Neither is proof of an end-to-end independent audit offering.

- https://github.com/pvlib/pvlib-python
- https://github.com/pvlib/pvlib-python/blob/main/LICENSE
- https://github.com/pvlib/pvanalytics

## Competitive displacement check

This isn't a greenfield opening. Raptor Maps already provides solar asset health analytics and workflows, while Solargis supplies performance monitoring and independent benchmarking tools. Our hypothetical narrower wedge is a **one-off, explainable, source-auditable independent second opinion for smaller rooftop operators**. That wedge must be *tested against actual offers, prices and buyer switching behaviour*, not assumed to exist.

- https://raptormaps.com/products/solar-management-platform
- https://kb.solargis.com/v1/docs/pv-performance-monitoring

## Commercial route hypotheses

- **Internal reuse:** combine pvlib plus data-quality components with first-party measurement methods only after evidence and licensing review. First avoid duplicating competitors.
- **Fixed-scope paid diligence:** customer provides inverter exports, system specifications and data-use authorization. Return yield-vs-model deviation, missingness, alternative causes and a reviewed uncertainty section. No electrical safety or regulatory certification claim.
- **Later retainer:** recurring audits only if one-off customers renew voluntarily.

### Illustrative *not observed* unit economics

| Assumption | TWD per completed report |
| --- | ---: |
| Quoted hypothetical price | 25,000 |
| Hypothetical direct delivery cost | 16,000 |
| Gross contribution before acquisition, hosting, tax and overhead | 9,000 |
| Gross contribution margin | 36% |

These values are **an arbitrary stress-test fixture**, not a market price, quote, willingness-to-pay observation, signed deal, or income forecast.

## What a useful first commercial signal looks like

1. Obtain one identifiable operator's authorization to assess real data and verify that the issue matters to them.
2. Compare the task and delivered evidence with a generic-model research workflow and at least one existing monitoring service.
3. Measure analyst time, external-data cost, total delivery expense, errors and decisions changed.
4. Ask for an explicit paid pilot **only if** the independent assessment offers a demonstrable improvement; capture refusal and competitor substitution as negative outcomes.

**Automatic decision today:** evidence lead only; no verified customer demand; no implementation validation; license not yet reviewed for our intended distribution; no observed margin or underconversion.

## Portfolio comparison

Cite–Refinery's earlier Open Food Network example has a more concrete upstream service route (a published paid-contributor application, though not a contract). The PV case has potentially different customer economics but materially weaker actual buyer evidence. Avoid promoting PV above OFN solely because PV's hypothetical invoice is larger.

## Reproduction

```bash
python -m unittest tests.test_pv_opportunity_conversion -v
PYTHONPATH=src python -m cite_refinery.opportunity_cli \
  research_materials/opportunity_conversion/pv-independent-rooftop-performance-audit.json \
  --format markdown
```

The evaluator tests evidence-constrained *decision output*, not the source quality of external studies, working PV technical performance, competitor completeness, or actual revenue. No field validation or external contact was performed in this experiment.
