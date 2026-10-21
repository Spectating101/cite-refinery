# Cite–Refinery | Emergent capability conversion atlas

**Source net:** 605 surveyed repositories (36 examined in this stratified slice), 8 emergent problem/research areas, 63 underlying public records.

**Candidate relationships are hypotheses**. Neither underconversion nor independently proven technical quality, actual adoption failure, real benefit or paid economic spread was established.

## Potential non-obvious connections

### CV-01 — asset to problem

**Possible connection:** river-wise turns NOAA NWPS gauge stage and forecast data, with flood thresholds and impact statements, into a household-level display. FIMserv generates flood inundation maps. Combined, a gauge forecast crossing a threshold could trigger a pre-computed or on-demand inundation map. That would give a location-specific alert, not a river-wide one. It could also record when and where alerts fire.

**Why non-obvious:** The shared mechanism is a threshold-to-impact lookup. Gauge stage maps to inundation extent, and extent maps to an impact statement. A home-automation UI and a hydrologic mapping tool both depend on this mapping, but they use different vocabularies and have different audiences.

**Underconversion cause to investigate:** integration — The two tools may be unconnected because of different user communities, gauge-to-reach ID mismatches, and unclear coverage of FIMserv outputs. The AGPL-3.0 licence on FIMserv may also complicate combination, though this is unverified.

**Potential recombination or use:** Pick one NWPS gauge. Pre-generate FIM maps for 3-4 stage levels with FIMserv. Show the matching map in a small prototype next to river-wise's threshold display. Check the stage-to-map correspondence against NWPS's own impact statements for that gauge.

**Potential value:** technical_capability, public_benefit, research_knowledge

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** For one gauge, compare FIMserv extents at the NWPS flood-category stages with the NWPS impact statements. If the inundated areas contradict the published impacts, or the gauge-to-reach mapping cannot be resolved without manual work, drop the link.

**Original repository/source IDs:** github:TheWillMiller/river-wise, github:sdmlua/FIMserv, EPMC-871d10af9889, OFFICIAL-dbee83ba8137, OA-4ecb63fe5958c9

### CV-02 — asset to problem

**Possible connection:** pool-monitor-card shows up to 25 parameters at a glance in Home Assistant. Its card pattern could be reused for indoor environment data such as CO2, humidity and PM, with thresholds and logging. This would address the gap in standardized exposure data and exposure-controlled tracking in homes and classrooms.

**Why non-obvious:** Pool chemistry and indoor air both need many parameters judged against acceptable ranges, with drift over time. The transferable piece is multi-parameter range display, not the pool domain. Whether it fits indoor air is open: the sensor types, units and thresholds differ.

**Underconversion cause to investigate:** no_demonstrated_need — Generic Home Assistant air-quality cards may already cover this, and no source shows demand from schools or households for a pool-card derivative. The apparent potential may be false.

**Potential recombination or use:** Configure the card with a few sensor entities (CO2, RH, PM2.5), using ranges from the cited literature or guidance, for one room. Log exceedance durations as a minimal exposure record.

**Potential value:** public_benefit, research_knowledge, operational_efficiency

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Check whether the card's configuration schema accepts arbitrary non-pool sensors with custom ranges. Also check whether an existing indoor-air card already offers equivalent per-parameter range display. If either check fails, the link has no value.

**Original repository/source IDs:** github:wilsto/pool-monitor-card, EPMC-15ee874ecc38, EPMC-e2f3b5123391, OA-a22f19815c0834

### CV-03 — asset to asset

**Possible connection:** The lead-time skill models stochastic lead times and stockout probability by Monte Carlo simulation, then sets safety stock. The same Monte Carlo and buffer-sizing logic might be adapted to cold-chain or perishable supply problems, using spoilage-limited lead times as the stochastic input.

**Why non-obvious:** Both tools generate synthetic outcomes from stochastic parameters and read off a probability of failure. A safety-stock buffer plays the role of a coverage margin. Eidolon's role is weak, and the repo pairing may be spurious. The better transfer is the lead-time skill applied to the food rescue domain (see CV-04).

**Underconversion cause to investigate:** missing_evidence — No source shows that the two are comparable or that the pairing has any use. It is probably false potential, and I include it only to flag it. I would drop it first.

**Potential recombination or use:** Do not pursue Eidolon. Test only whether the skill's simulator accepts a distribution other than vendor lead time.

**Potential value:** internal_portfolio

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Read the skill's input schema. If it cannot take custom distributions, or if it has no output beyond a point reorder trigger, discard this hypothesis.

**Original repository/source IDs:** github:alphaparkinc/genpark-agentic-commerce-vendor-lead-time-po-safety-stock-skill, github:ncsa/eidolon

### CV-04 — asset to problem

**Possible connection:** Food rescue networks have uncertain pickup timing and perishable stock. A lead-time variability model with stockout-probability simulation could estimate the chance that a pantry runs short of a category of food, and how much buffer from rescue streams would prevent it. This would shift the metric from tonnage rescued towards a recipient-side measure of availability.

**Why non-obvious:** Both settings have an uncertain supply arrival, a demand that must be met, and a probability of running out. The skill is built for commercial reorder, but the structure resembles pantry replenishment under random donation arrivals. The perishability constraint is absent from the skill and has to be added.

**Underconversion cause to investigate:** missing_evidence — The sources report gross tonnage and not arrival-time distributions or stock levels. Donated food is not procured on contract, so lead-time models may not fit. No demand is shown for this analysis.

**Potential recombination or use:** Obtain a sample of pickup and delivery timestamps from one rescue operator, with consent, or use public data. Fit an arrival distribution and run the skill's simulation. Check whether predicted shortages match recorded shortages.

**Potential value:** operational_efficiency, public_benefit, research_knowledge

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** On a held-out period of pickup logs, check whether the model's predicted stockout frequency is closer to the observed one than a naive constant-rate baseline. If it is not, the approach adds nothing.

**Original repository/source IDs:** github:alphaparkinc/genpark-agentic-commerce-vendor-lead-time-po-safety-stock-skill, EPMC-7deb988ae2ab, OA-88cafd9405fbed, OA-8e75d5d1b1f35b

### CV-05 — asset to problem

**Possible connection:** The cholera package uses Voronoi and Delaunay methods to assign cases to nearest pumps (neighbourhoods) in the 1854 data. A similar nearest-point partition could define vaccination catchment zones for CNVR campaigns, and could be used to check coverage gaps. The AED map backend contributes a pattern for serving point locations as vector tiles from OSM.

**Why non-obvious:** Nearest-facility partitioning of space, whether pumps, AEDs or vaccination points, is the shared mechanism. The rabies sources discuss zoned CNVR and porous borders. Voronoi zoning would put boundaries where dogs can realistically cross them, but that needs movement data.

**Underconversion cause to investigate:** missing_evidence — The rabies sources report no verified deployed intervention or outcome, and no spatial dog-density data appears in the slice. Voronoi zones on pumps may not carry over to mobile animals.

**Potential recombination or use:** Use public dog-population or vaccination-point data for one district and compute Voronoi catchments. Compare with the zones actually used in a documented campaign.

**Potential value:** research_knowledge, public_benefit

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Using any documented campaign with recorded vaccinated-dog locations, test whether Voronoi catchments predict where coverage fell below the 70% target better than the campaign's administrative zones. If not, drop it.

**Original repository/source IDs:** github:lindbrook/cholera, github:openstreetmap-polska/openaedmap-backend, EPMC-088e66a2f887, OA-3c3cd5c7fc6491, OA-d94945c2bf53f3

### CV-06 — asset to asset

**Possible connection:** Shipfox runs coding agents like CI pipelines, and Polylogue archives agent conversation histories with audit trails. Combining them would let pipeline runs of agents leave searchable, auditable evidence. That evidence could be used to check agent behaviour after a failure.

**Why non-obvious:** CI systems treat logs as run artifacts, while Polylogue treats agent history as an evidence store. The mechanism is an artifact-provenance interface: a run ID linking a pipeline step to an archived transcript. The vocabularies differ (CI versus digital archive).

**Underconversion cause to investigate:** integration — The formats of Shipfox run logs and Polylogue's import formats may not match. Both are small projects, so maintenance may be uncertain. Demand is unknown.

**Potential recombination or use:** Run one Shipfox job that invokes a supported agent, export its log, and attempt to ingest it into Polylogue. Check that the run ID can be traced back.

**Potential value:** technical_capability, internal_portfolio, operational_efficiency

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Try the ingestion with one real run. If Polylogue cannot parse the log without writing a custom importer larger than a small script, or if the run cannot be traced to a pipeline step, the link is not low-cost.

**Original repository/source IDs:** github:Sinity/polylogue, github:ShipfoxHQ/shipfox

### CV-07 — domain to domain

**Possible connection:** Both domains record that early warning systems exist but that no source shows measured reductions in morbidity or mortality, and that evaluation designs lack controls. A shared evaluation design could apply to both: stepped or staggered rollout of warning thresholds, comparing outcomes before and after across zones, with warning-issued and warning-received logged as separate measurements.

**Why non-obvious:** The shared constraint is that a warning only helps if it is both issued and acted upon, so the evaluation has to measure the chain from forecast to alert to behaviour. Heat and flood differ in onset speed, which the flood sources distinguish (rapid versus slow onset), so onset speed may be a moderating variable.

**Underconversion cause to investigate:** missing_evidence — The slice shows no measured intervention outcome for either domain, and it states a bias towards high-income countries. Whether a shared protocol is feasible is unknown.

**Potential recombination or use:** Write a one-page protocol listing the measurements common to both: alert issue time, receipt rate, protective action rate, and outcome. Compare with the design of one published evaluation in each domain.

**Potential value:** research_knowledge, public_benefit, institutional_capacity

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Check whether any published heat or flood early-warning evaluation already reports alert receipt and action rates separately. If they all do and still show no effect, or none can be reconciled into one protocol, the analogy adds nothing.

**Original repository/source IDs:** EPMC-0715c73feecf, OA-d26245f891f838, OFFICIAL-194f3653ddf1, EPMC-871d10af9889, OFFICIAL-dbee83ba8137

## Discovery limits

In this slice I found no mechanism-level links for the lithium-ion battery regeneration domain, the e-waste toxicant exposure domain, or the gig-worker algorithmic management domain. Several repositories also stayed unlinked: the DDoS and flood-attack tools, the CAD repositories, the bot-protection, CT-log and SOC tooling, the dbt control plane, McCode, the finance and tokenomics repositories, the church website, and the translation and dictation apps. Nothing here says such links do not exist elsewhere. CV-03 is weak and is listed only as a candidate to drop.

This is a proposal map over a bounded stratified sample, not proof that these projects are actually good, neglected or freely reusable. Require original tests, licenses, integration evidence, field need and independent review before accepting any relationship.
