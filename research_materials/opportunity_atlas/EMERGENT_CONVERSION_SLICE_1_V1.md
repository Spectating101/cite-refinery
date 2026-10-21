# Cite–Refinery | Emergent capability conversion atlas

**Source net:** 605 surveyed repositories (36 examined in this stratified slice), 8 emergent problem/research areas, 63 underlying public records.

**Candidate relationships are hypotheses**. Neither underconversion nor independently proven technical quality, actual adoption failure, real benefit or paid economic spread was established.

## Potential non-obvious connections

### CV-01 — asset to problem

**Possible connection:** FishMaster's pipeline (ESP32 sensor node, MQTT, SSE streaming, PostgreSQL time series, React dashboard) is a general low-cost sensor-to-dashboard stack. In principle it could be re-targeted from water-quality channels to classroom CO2, humidity and particulate channels. That would give time-resolved exposure data, which the atlas says is missing from cross-sectional studies. The transferable mechanism is continuous, threshold-exceedance logging with live alerting.

**Why non-obvious:** Aquarium water chemistry and classroom bioaerosol exposure use different vocabulary. Mechanically, both need a drifting sensor, an exceedance-duration metric, and a real-time push to a non-expert. The atlas gap is the lack of standardized exposure-response thresholds and longitudinal tracking, not a lack of sensors.

**Underconversion cause to investigate:** missing_evidence — The pipeline may be demo-grade. Its sensor drivers are probably aquatic, so it may lack CO2 and PM calibration and validation against reference instruments. The atlas also shows no demonstrated school demand.

**Potential recombination or use:** Fork the firmware to read a low-cost NDIR CO2 sensor and a PM sensor. Co-locate it with a reference monitor for 2 weeks in one room or home, log CO2-exceedance minutes, and compare the two. This is a self-use pilot with no school partnership required.

**Potential value:** technical_capability, public_benefit, internal_portfolio

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Co-locate 2 nodes with a reference CO2 monitor for 7 days. If the nodes' error stays above about 100 ppm after simple calibration, or the MQTT/SSE path drops more than 5% of samples, the idea is refuted.

**Original repository/source IDs:** github:ALNezar/FishMaster, EPMC-15ee874ecc38, OA-1139840a6d83ac, OFFICIAL-04c6c3a2a87e

### CV-02 — asset to asset

**Possible connection:** The MES ingests OPC UA data and computes OEE and SPC. The home-energy skill models thermal inertia and shifts load against price signals. The two could be combined as a shared flexible-load scheduler. Process-equipment state and an SPC quality envelope would define how far a job may be delayed. A tariff or peak signal would then choose the schedule within that envelope.

**Why non-obvious:** One tool is a factory execution system and the other is a consumer energy agent. The shared mechanism is constraint-bounded deferral. A thermal-inertia comfort band in one case and a quality or throughput tolerance in the other both act as slack that a price signal can use.

**Underconversion cause to investigate:** integration — The two projects have different data models (ISA-95 versus household tariffs). Industrial load flexibility also needs per-process constraints that neither repo is described as having. Nobody may have an actual need for it.

**Potential recombination or use:** Build an offline simulation. Use synthetic OPC UA machine states and a public TOU tariff, have the agent propose schedules through the MCP tools, and check that the quality and OEE constraints hold.

**Potential value:** technical_capability, operational_efficiency, internal_portfolio

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** On a simulated 24h trace, check that deferring jobs lowers cost without breaching OEE or SPC limits. If the feasible deferral window under realistic constraints is near zero, drop it.

**Original repository/source IDs:** github:factorysemantics/factorysemantics-mes, github:Alpha-Park/genpark-personal-agent-dynamic-home-energy-spot-tariff-arbitrage-skill

### CV-03 — research to asset

**Possible connection:** The atlas flags weak data interoperability and a lack of real-time field validation in flood warning systems in resource-limited settings. lneto is a heapless TCP/IP, NTP and DHCP stack described as running in a few kB of RAM. In principle it could be the networking layer for very cheap water-level nodes. The node would send timestamped readings over Ethernet or an equivalent link.

**Why non-obvious:** A network stack is rarely linked to flood-warning validation. The relevant mechanism is NTP time sync with a small memory footprint. Warning-lead-time evaluation needs reliable timestamps across many dispersed nodes, which is a measurement-integrity problem.

**Underconversion cause to investigate:** no_demonstrated_need — Flood programs may already use commercial telemetry. Wired Ethernet may not suit field sites. The stack may not support the radios that are actually used.

**Potential recombination or use:** Run a bench test: an MCU with lneto posts timestamped readings from a water-level sensor to a collector. Measure the clock offset against a reference over several days.

**Potential value:** technical_capability, research_knowledge, public_benefit

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Run NTP sync on a small MCU for 72h. If median clock error exceeds about 1 s, or the node needs more RAM than the claimed few kB, the use case is refuted.

**Original repository/source IDs:** github:soypat/lneto, EPMC-871d10af9889, OFFICIAL-dbee83ba8137, OA-0b799176aa3262

### CV-04 — research to asset

**Possible connection:** OnCo is a cited knowledge graph with typed pages, an API and an MCP server. The rabies atlas theme has explicit evidence-limit fields: an underpowered serology cohort (n=16), a 56.3% seroconversion figure, and a conceptual vacuum-effect model. These could be encoded as typed claim nodes with sample size and evidence-grade attributes. The goal is a template for one-health evidence graphs that expose quantitative evidence gaps.

**Why non-obvious:** Oncology and veterinary public health look unrelated. The shared mechanism is graph schema design that attaches statistical power and evidence limits to each claim, so that weak claims such as 70% coverage versus 56.3% protective titer can be queried.

**Underconversion cause to investigate:** coordination — The OnCo scope is oncology and its maintainers may not want other domains. Extracting structured claims from papers needs curation effort that nobody may have committed to.

**Potential recombination or use:** Try this as an internal portfolio exercise. Encode about 20 claims from the 6 rabies sources in OnCo's schema, or a clone of it. Then run queries such as 'claims with n<30'.

**Potential value:** research_knowledge, coordination, internal_portfolio

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Hand-encode the claims from 6 sources. If the schema cannot represent sample size, threshold and evidence limit without changes to its core, or the queries give no more than a plain spreadsheet, drop it.

**Original repository/source IDs:** github:judegomila/OnCo, EPMC-088e66a2f887, OA-3c3cd5c7fc6491, EPMC-7329c77af95d

### CV-05 — asset to problem

**Possible connection:** FreddyFridge tracks household food expiry. The MES computes OEE-style metrics from machine state. The atlas notes that surplus-redistribution metrics count tonnage rather than recipient outcomes. A pantry-level loss-accounting model could borrow the OEE decomposition (availability, performance, quality) and apply it to donated food: usable-before-expiry fraction, delivery time, and fraction actually consumed.

**Why non-obvious:** OEE is a manufacturing metric. Its mechanism is splitting total loss into separable, attributable stages. That would expose where redistributed food is lost (cold chain, date labeling, non-uptake) instead of one gross-tonnage figure. FreddyFridge is only a source of an expiry-tracking data model.

**Underconversion cause to investigate:** missing_evidence — The atlas says nutritional uptake data is not collected. No food bank has a stated need for this decomposition, and recipient consumption is hard to measure.

**Potential recombination or use:** Apply the loss decomposition to an already-published pilot dataset, such as the 847 kg IoT pilot if the data is accessible. Report loss by stage and compare with the gross figure.

**Potential value:** research_knowledge, operational_efficiency, public_benefit

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Check whether any published food-rescue dataset has stage-level timestamps and quantities. If none does, the decomposition cannot be computed and the idea is refuted for now.

**Original repository/source IDs:** github:nadar71/FreddyFridge, github:factorysemantics/factorysemantics-mes, EPMC-7deb988ae2ab, EPMC-826342b4eec2, OA-88cafd9405fbed

### CV-06 — asset to asset

**Possible connection:** Fieldcraft is a Rust FEA, heat-transfer and lattice-Boltzmann solver whose results are checked against theory. Tesseract-core packages differentiable scientific components behind container and RPC interfaces. Wrapping a Fieldcraft solver as a Tesseract component would be a way to test whether gradients through the solver (via a differentiable wrapper or adjoint) can support design optimization.

**Why non-obvious:** The mechanism is an interface contract: a solver exposed as a callable component with defined inputs, outputs and optionally a vector-Jacobian product. This would let an optimizer in a different language drive the Rust solver without rewriting it.

**Underconversion cause to investigate:** integration — The Rust solver may not expose derivatives, and finite-difference gradients through implicit nonlinear solves can be noisy. The two projects may never have been combined.

**Potential recombination or use:** Wrap one simple heat-conduction case as a Tesseract and compare finite-difference gradients with analytic gradients for a 1D problem.

**Potential value:** technical_capability, internal_portfolio

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** On a 1D conduction case with a known analytic gradient, check whether finite-difference gradients from the wrapped solver agree to within about 1%. If they don't, or the wrapper can't be built in a day, drop it.

**Original repository/source IDs:** github:tangency-labs/fieldcraft, github:pasteurlabs/tesseract-core

### CV-07 — domain to domain

**Possible connection:** The heat theme says macro climate models cannot capture the personal thermal exposure of outdoor workers. The gig-work theme says dynamic time penalties raise injury risk but there is no platform telemetry audit. Both gaps are measurement problems about the same population. The platform's dispatch records could in principle serve as a proxy for how long workers are outdoors during heat events, if the platform shared them. The shared constraint is exposure-time estimation without personal sensors.

**Why non-obvious:** Heat-health epidemiology and labor platform research use different methods. The mechanism is joining time-at-work trajectories with weather to get exposure-weighted hazard. This addresses both literatures' stated gaps (no personal exposure, no telemetry).

**Underconversion cause to investigate:** rights — Platform telemetry is proprietary, and there may be privacy and consent obstacles. Platforms may have no incentive to share it.

**Potential recombination or use:** Use a public or consented dataset, such as courier-submitted logs, with gridded weather. Check whether delivery activity falls or workers keep working in extreme heat.

**Potential value:** research_knowledge, public_benefit

**Quality evidence status:** not_independently_tested; **actual conversion status:** unknown_not_measured

**First falsification:** Look for any open courier activity dataset with timestamps and location. If none exists at city resolution, or activity shows no relationship to temperature, the proxy idea is weakened.

**Original repository/source IDs:** EPMC-0715c73feecf, OA-ba418ee71ac82d, EPMC-83a764d60470, OA-6642b2dc88be44

## Discovery limits

In this slice, the lithium-ion battery regeneration and e-waste toxicant themes, and repositories such as the circRNA pipeline, Atomsk, WorshipCommons, badip, the Eagle library and the geospatial servers, got no defensible mechanism-level links. They are left unlinked here, which is not a claim about the wider corpus.

This is a proposal map over a bounded stratified sample, not proof that these projects are actually good, neglected or freely reusable. Require original tests, licenses, integration evidence, field need and independent review before accepting any relationship.

## Optional enabling resources (not a fourth layer)

These are discovery channels only, not awarded grants, verified eligibility or financing matches.

- **NLnet open technology grant application channel** — grant_program: Publisher page lists next submission deadline 2026-11-03 12:00 CET; individual fund availability must be reconfirmed. Eligibility: Open licensing and specific EU program conditions apply; the funder states it is not interested in AI-generated projects or proposals. No user or project eligibility checked.
- **GitHub Sponsors for open-source maintainers** — sponsorship_platform: Public documentation describes contributor sponsorship rather than a guaranteed grant or investment. Eligibility: Maintainer account, supported jurisdiction, identity and payout compliance required; project or user's eligibility not checked.
- **Open Collective fiscal sponsorship and shared accounting** — fiscal_host: Open Source Collective invites qualifying projects to apply and advertises 10 percent fiscal-host fee. Eligibility: Fiscal hosting enables collection and expenditure administration but is not itself a grant award or committed sponsor.
- **Grants.gov official US federal funding opportunity directory** — grant_directory: Official search and eligibility information for specific notices; no active matching notice selected. Eligibility: US program notices contain their own applicant-type and geographic conditions; a university or project based in Taiwan has no assumed eligibility.
- **FINDIT Taiwan government-backed startup investment information** — investment_route: Public investment and matchmaking information platform, not a promised investor or particular open round. Eligibility: Taiwanese startup/overseas Taiwanese founder registration and specific matchmaking event rules can apply; personal, student and project eligibility unverified.
- **CSG (user-named funding source; expansion unverified)** — unresolved_source: Name supplied as a possible funding source; no authoritative expansion or official record established. Eligibility: Unknown source and scheme; eligibility, jurisdiction, deadlines and whether grants or investment are offered are unknown.
