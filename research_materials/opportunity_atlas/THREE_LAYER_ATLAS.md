# One graph, three evidence layers

**Practical reality ⇄ Academic explanations ⇄ Implementations/solutions**

The relationships below form **one typed query view**, not two independent research networks. Evidence sources are attached as provenance, not promoted to a fourth conceptual layer. Commercial conversion is an analysis performed on this graph, not another fundamental layer.

## Coverage of current bounded inputs

| Layer | Source-bounded records |
|---|---:|
| Practical | 21 |
| Academic (proposed mechanisms) | 8 |
| Implementations (candidate capabilities) | 21 |

All three layers are represented for 7 problem records. This **does not establish** that the proposed explanations or capabilities are correct. There are no independently validated end-to-end solutions or confirmed paying customers in this dataset.

## Readable problem paths

### Problem: battery recycling economics

**Practical:** Battery recycling profitability varies with pack design, logistics, labor and recovery process; a technically feasible regeneration method is not a validated profitable operation.

**Academic (hypothesis, not independent proof):** Disassembly and transport costs, recycling route, material recovery yield and hazard-control overhead interact with regional prices; cathode restoration alone cannot settle the processing margin.

**Implementation candidates / exclusions:**
- github:lingrany/EverBatt-LFP-Recycling-Analysis (POSSIBLE_PARTIAL_IMPLEMENTATION): Candidate: model_candidate_only

**Three layers represented:** yes; **end-to-end validated:** no; **buyer validated:** no.

### Problem: classroom ventilation outcomes

**Practical:** Schools can show high indoor CO₂ and respiratory burden without evidence that a given sensing or ventilation intervention improves clinical outcomes in those classrooms.

**Academic (hypothesis, not independent proof):** CO₂ is primarily an occupancy/ventilation proxy rather than a direct measurement of all particles, molds or pathogens; source exposure and response mechanisms differ.

**Implementation candidates / exclusions:**
- github:ajlongshanks/co2_esphome (POSSIBLE_PARTIAL_IMPLEMENTATION): Candidate: measurement_component_only

**Three layers represented:** yes; **end-to-end validated:** no; **buyer validated:** no.

### Problem: dog population identity and movement

**Practical:** Free-roaming dog counts and vaccination campaigns need individual/temporal reconciliation and movement understanding, while program outputs do not alone establish sustained population or rabies effects.

**Academic (hypothesis, not independent proof):** Births, deaths, immigration, ownership changes and observation effort affect apparent abundance; vaccination coverage and campaign effort require distinct denominators.

**Implementation candidates / exclusions:**
- github:kobotoolbox/kpi (POSSIBLE_PARTIAL_IMPLEMENTATION): Candidate: data_capture_infrastructure_only

**Three layers represented:** yes; **end-to-end validated:** no; **buyer validated:** no.

### Problem: ewaste toxicant control

**Practical:** Informal and formal electronic recycling expose workers and communities to metals and flame retardants, while an environmental modeling toolkit cannot replace occupational monitoring or hazard controls.

**Academic (hypothesis, not independent proof):** Thermal/mechanical dismantling disperses dust, volatile compounds and contaminated material streams; exposure depends on process conditions and worker protection.

**Implementation candidates / exclusions:**
- github:brightway-lca/brightway2 (POSSIBLE_PARTIAL_IMPLEMENTATION): Candidate: lifecycle_accounting_adjacent

**Three layers represented:** yes; **end-to-end validated:** no; **buyer validated:** no.

### Problem: flood warning to impact

**Practical:** Flood vulnerability and community early-warning deployments can be documented separately without knowing whether warnings prevented injury, drowning, displacement or service disruption.

**Academic (hypothesis, not independent proof):** Rainfall and water-level forecasts must be translated into geographically appropriate lead times, accessible warnings and practical evacuation/health-facility response.

**Implementation candidates / exclusions:**
- github:WeixuanZ/flood-warning-system (POSSIBLE_PARTIAL_IMPLEMENTATION): Candidate: forecast_interface_prototype

**Three layers represented:** yes; **end-to-end validated:** no; **buyer validated:** no.

### Problem: food redistribution outcomes

**Practical:** Food redistribution programs often measure recovered kilograms or pickup performance while actual beneficiary nutritional and net lifecycle benefits remain insufficiently linked to real operations.

**Academic (hypothesis, not independent proof):** Redistribution changes supply-chain routing, storage energy, spoilage and beneficiary access; causal and environmental effects depend on which food would otherwise be wasted or purchased.

**Implementation candidates / exclusions:**
- github:openfoodfoundation/openfoodnetwork (POSSIBLE_PARTIAL_IMPLEMENTATION): Candidate: adjacent_distribution_platform

**Three layers represented:** yes; **end-to-end validated:** no; **buyer validated:** no.

### Problem: heat warning to protective action

**Practical:** Heat mortality projections and early-warning plans are widespread sources of concern, but a meteorological warning is not itself evidence that vulnerable households received or acted on protection.

**Academic (hypothesis, not independent proof):** Heat hazards affect people differently by age, occupation, housing and access to cooling; forecasting only supplies one input to risk communication and response.

**Implementation candidates / exclusions:**
- github:open-meteo/open-meteo (POSSIBLE_PARTIAL_IMPLEMENTATION): Candidate: weather_data_component_only

**Three layers represented:** yes; **end-to-end validated:** no; **buyer validated:** no.

### Problem: gig worker algorithmic harm

**Practical:** Food-delivery platforms face reported accident and health risks associated with workload and algorithmic management; no listed software implementation here is independently shown to reduce worker injury.

**Academic (hypothesis, not independent proof):** Automated task assignment and incentives interact with deadline pressure, fatigue, road exposure and worker autonomy; descriptive sentiment data alone cannot isolate causal impacts.

**Implementation:** no linked capability candidate in this sample.

**Three layers represented:** no; **end-to-end validated:** no; **buyer validated:** no.

**Evidence gaps:** No source-grounded technical implementation proposed

### Published notice: 404621-2026

**Practical:** Luxembourg – Compliance software development services – Operational Risk Management Software

**Academic:** no source-bounded mechanism attached in this sample.

**Implementation candidates / exclusions:**
- github:koala73/worldmonitor (LIKELY_WRONG_FIT): koala73/worldmonitor

**Three layers represented:** no; **end-to-end validated:** no; **buyer validated:** no.

**Evidence gaps:** No established matching scientific explanation attached to this institutional requirement

### Published notice: 434418-2026

**Practical:** Ireland – Software package and information systems – UCC-2025-02 Provision of an Enterprise Risk Management Software System

**Academic:** no source-bounded mechanism attached in this sample.

**Implementation candidates / exclusions:**
- github:openbq-org/OpenBB (LIKELY_WRONG_FIT): openbq-org/OpenBB

**Three layers represented:** no; **end-to-end validated:** no; **buyer validated:** no.

**Evidence gaps:** No established matching scientific explanation attached to this institutional requirement

## Architecture boundary

This projection is **read-only** and does not yet migrate the separate source products into a transactionally backed persistent SemanticGraph. The original native store still permits neutral nodes and uses program for solution/implementation. The next ingestion gate should normalize those terms, preserve source provenance and require human approval before any status upgrade.

Some real connections are absent. The output must not infer a scientific link to a published requirement solely because the institution and an unrelated research abstract share words.
