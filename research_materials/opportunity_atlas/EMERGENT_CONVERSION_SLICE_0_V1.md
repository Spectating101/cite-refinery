# Cite–Refinery | Emergent capability conversion atlas

**Source net:** 605 surveyed repositories (35 examined in this stratified slice), 8 emergent problem/research areas, 63 underlying public records.

**Candidate relationships are hypotheses**. Neither underconversion nor independently proven technical quality, actual adoption failure, real benefit or paid economic spread was established.

## Potential non-obvious connections

### CV-01 — asset to problem

**Possible connection:** Hourly grid carbon-intensity (gCO2eq/kWh) time series could be used as an exogenous input to the techno-economic and lifecycle models for battery regeneration. Hydrothermal regeneration and recycling flowsheets are energy-intensive. Their per-kWh margin, which the sources report between -$21.43 and +$21.91, and their net emissions may depend on when and where the process runs. A carbon-aware scheduler for batch regeneration is the practical form of this idea.

**Why non-obvious:** The shared mechanism is time-varying marginal electricity attributes acting on a batch process whose start time can be moved. The battery literature treats electricity as a fixed cost, while the carbon API treats loads as software workloads.

**Underconversion cause to investigate:** no_demonstrated_need — Recycling operators may be indifferent to hourly carbon intensity. Electricity may be a small share of the margin variance compared with feedstock and pack heterogeneity. The API covers France only, and the reported regeneration data are benchtop scale.

**Potential recombination or use:** Take the published energy-per-kg figures for hydrothermal regeneration. Convolve them with a year of French hourly intensity to estimate the spread in gCO2eq per kWh of cathode between best-case and worst-case scheduling windows. Compare that spread with the model's margin uncertainty.

**Potential value:** research_knowledge, technical_capability, public_benefit

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Desk calculation: if shifting a regeneration batch within a 24-hour window changes the lifecycle emissions or cost by less than 5% of the existing sensitivity range, reject the idea.

**Original repository/source IDs:** github:Kovelt/carbon-fr, EPMC-1d4b60c85f48, EPMC-5e474470179c, OA-53d2760b3abab4

### CV-02 — asset to problem

**Possible connection:** Nongor is an offline phone-to-phone signed SOS system with flood-avoiding routing. It could act as a last-mile warning and response data channel for flood early warning systems that lack field validation. Signed mesh messages would give timestamped, geolocated records of where and when people were affected. Those records could serve as outcome telemetry. The atlas says no audited reduction in flood-related disease or mortality is documented, and controlled evaluation is missing.

**Why non-obvious:** The flood literature lacks measurement infrastructure for outcomes in connectivity-poor settlements. The mesh app was built for victims rather than evaluators. Signed message logs give an observation mechanism that does not depend on internet or self-reported surveys.

**Underconversion cause to investigate:** missing_evidence — No field trials are evident. Mesh range and density needs are unknown. Privacy and consent issues for location logging are unresolved. Integration with an agency warning pipeline such as FFGS is unclear.

**Potential recombination or use:** Run a simulated drill with a handful of devices. Replay the timing of a rapid-onset versus slow-onset flood scenario and test message delivery latency and loss. Check whether the aggregated signed logs can reconstruct an exposure timeline without a server.

**Potential value:** public_benefit, research_knowledge, institutional_capacity

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** In a controlled multi-device test with realistic obstruction, if message delivery success is below roughly 80% across hops, or if routing and log reconstruction cannot be done without a server, drop the idea as an evaluation channel.

**Original repository/source IDs:** github:AuvroIslam/Nongor, EPMC-871d10af9889, OA-0b799176aa3262, OFFICIAL-dbee83ba8137

### CV-03 — asset to asset

**Possible connection:** GridShadow ranks defensive chokepoints in cyber-physical attack graphs, using pandapower models. The Jackery Home Assistant integration exposes residential solar and battery device state and controls. Together, a distributed behind-the-meter storage fleet could be modeled as a new node class in the attack-graph generator. The question would be which cloud or local control paths from consumer IoT could produce physical grid impact.

**Why non-obvious:** The shared interface is a controllable power injection or withdrawal point reachable through a network. One repo is a threat-modeling formalism, and the other is a consumer device adapter.

**Underconversion cause to investigate:** integration — A single household device is probably too small to cause grid impact. The effect would depend on aggregation, which is not shown. Home Assistant integration details may not map to attack primitives.

**Potential recombination or use:** Add a node type for aggregated DER with power limits taken from the integration's exposed entities. Sweep fleet penetration in a pandapower toy feeder and see whether any chokepoint ranking changes.

**Potential value:** research_knowledge, internal_portfolio

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** If chokepoint rankings in the toy feeder are unchanged at up to 20% DER penetration, reject the extension.

**Original repository/source IDs:** github:Krishita17/GridShadow, github:Bigdaddy1990/jackery_solarvault

### CV-04 — research to asset

**Possible connection:** Argos logs commands and hashes artifacts per case folder. The food-redistribution literature notes that evaluations track gross tonnage but not provenance or outcome. A hash-logged chain-of-custody pattern could be borrowed for pilot evaluation records, such as pickup events, sensor readings, and recipient-outcome follow-ups. The aim is audit-grade, tamper-evident evidence.

**Why non-obvious:** The mechanism is append-only, hash-verified evidence handling taken from OSINT casework and applied to program evaluation. It is not about OSINT content.

**Underconversion cause to investigate:** no_demonstrated_need — Food rescue groups may not need tamper-evident logs. Their limiting factor may be dietary outcome data, which hashing does not supply.

**Potential recombination or use:** Extract the logging and hashing pattern into a small script. Apply it to a mock pickup dataset and see whether auditors can verify the record without the operators.

**Potential value:** institutional_capacity, research_knowledge

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Ask two or three evaluators or operators whether tamper-evident logs would change their evaluation. If none says yes, drop the idea.

**Original repository/source IDs:** github:SOsintOps/Argos, EPMC-7deb988ae2ab, OA-88cafd9405fbed, OFFICIAL-86c5d4ade74b

### CV-05 — domain to domain

**Possible connection:** Both fields have a threshold-style target that is believed to work, with a measurement gap in the delivery step. Rabies uses 70% annual vaccination coverage, but only 56.3% of vaccinated dogs reach protective titers. Heat warning systems are deployed, but no measured outcome shows that they reduce mortality. In both cases the nominal coverage metric, such as vaccines given or warnings issued, is not the effective protective coverage. A shared measurement is effective coverage: nominal coverage multiplied by the fraction with verified protection or action taken.

**Why non-obvious:** Veterinary public health and climate-health warnings use different vocabularies. Both lack a verified step between delivery and protection, and both compute that gap the same way.

**Underconversion cause to investigate:** missing_evidence — The rabies serology cohorts are small, with n=16. Heat warnings lack intervention-control designs. The analogy might not hold because heat warnings are not immunity-like.

**Potential recombination or use:** Write the effective-coverage formula for each and run a sensitivity analysis. For rabies, show the herd-immunity margin under 56.3% seroprotection. For heat, define behavioral-response as the analogous multiplier and list which datasets could estimate it.

**Potential value:** research_knowledge, public_benefit

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Check whether the rabies transmission threshold remains satisfied at the effective coverage in published models. If it does, the rabies half of the analogy adds no new constraint.

**Original repository/source IDs:** EPMC-088e66a2f887, OA-3c3cd5c7fc6491, EPMC-0715c73feecf, OA-57bba7412a5fbd

### CV-06 — asset to problem

**Possible connection:** Transitland Atlas is a directory of open mobility feeds, including GBFS and MDS. It could provide a standardized, public description of shared micromobility and transit supply. That could be used as a contextual covariate for courier routing and exposure analysis, such as transit-gap zones. The atlas says independent platform telemetry is absent, so public mobility feeds might partly substitute for context.

**Why non-obvious:** Standardized feed registries are used for rider information. Here they would serve as an exposure covariate in occupational-harm research.

**Underconversion cause to investigate:** no_demonstrated_need — Courier harm is likely driven by platform dispatch penalties, which feeds do not capture. Transit availability may be a weak covariate.

**Potential recombination or use:** Pick one city with both feed coverage and published courier injury statistics. Test whether transit-gap exposure correlates with injury rates.

**Potential value:** research_knowledge

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** If no correlation or association is found in one city with adequate data, drop it.

**Original repository/source IDs:** github:transitland/transitland-atlas, EPMC-83a764d60470, OA-6642b2dc88be44

## Discovery limits

In this slice, the indoor air quality, e-waste toxicant, and soil-index (Open Bodem Index) areas were not linked to any specific candidate. Several ERP, EDA, robotics, ARPES, painterly-cartography and legal-intelligence repos were left unlinked because no precise shared mechanism was found. Nothing is claimed about areas outside this slice.

This is a proposal map over a bounded stratified sample, not proof that these projects are actually good, neglected or freely reusable. Require original tests, licenses, integration evidence, field need and independent review before accepting any relationship.

## Optional enabling resources (not a fourth layer)

These are discovery channels only, not awarded grants, verified eligibility or financing matches.

- **NLnet open technology grant application channel** — grant_program: Publisher page lists next submission deadline 2026-11-03 12:00 CET; individual fund availability must be reconfirmed. Eligibility: Open licensing and specific EU program conditions apply; the funder states it is not interested in AI-generated projects or proposals. No user or project eligibility checked.
- **GitHub Sponsors for open-source maintainers** — sponsorship_platform: Public documentation describes contributor sponsorship rather than a guaranteed grant or investment. Eligibility: Maintainer account, supported jurisdiction, identity and payout compliance required; project or user's eligibility not checked.
- **Open Collective fiscal sponsorship and shared accounting** — fiscal_host: Open Source Collective invites qualifying projects to apply and advertises 10 percent fiscal-host fee. Eligibility: Fiscal hosting enables collection and expenditure administration but is not itself a grant award or committed sponsor.
- **Grants.gov official US federal funding opportunity directory** — grant_directory: Official search and eligibility information for specific notices; no active matching notice selected. Eligibility: US program notices contain their own applicant-type and geographic conditions; a university or project based in Taiwan has no assumed eligibility.
- **FINDIT Taiwan government-backed startup investment information** — investment_route: Public investment and matchmaking information platform, not a promised investor or particular open round. Eligibility: Taiwanese startup/overseas Taiwanese founder registration and specific matchmaking event rules can apply; personal, student and project eligibility unverified.
- **CSG (user-named funding source; expansion unverified)** — unresolved_source: Name supplied as a possible funding source; no authoritative expansion or official record established. Eligibility: Unknown source and scheme; eligibility, jurisdiction, deadlines and whether grants or investment are offered are unknown.
