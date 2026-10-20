# Practical mechanisms ↔ scientific context ↔ reusable capabilities

Eight source-bounded operating-problem dossiers spanning research, engineering, health, environment, logistics and work. **These are not eight validated commercial opportunities.** Every publication excerpt was compared with the original text and SHA-256 in a development-only source dump; every named repo's README was checked against its saved git blob. Neither step validates scientific entailment or tests real-world implementation.

Source identities checked: 31; README blobs: 7; tested end-to-end integrations: 0; verified paying customers: 0.

## Battery Recycling Economics

**Observed or documented problem (source-bounded):** Battery recycling profitability varies with pack design, logistics, labor and recovery process; a technically feasible regeneration method is not a validated profitable operation.

**Mechanism being investigated:** Disassembly and transport costs, recycling route, material recovery yield and hazard-control overhead interact with regional prices; cathode restoration alone cannot settle the processing margin.

**Required capability contract:** Parameter-sensitive route comparison plus physical safety controls and measurable material recovery yields, with scenario assumptions explicit.

**Falsifying/decisive measurement:** Compare route net margins under realistic regional labor/transport/collection conditions; report failure-path hazard and processing costs instead of extrapolating lab yield.

**Original-source context and limitations:**

- [Financial viability of electric vehicle lithium-ion battery recycling](https://doi.org/10.1016/j.isci.2021.102787) — *$·kWh −1 but strongly depends on transport distances, wages, pack design and recycling method. Comparing commercial battery packs, the Tesla Model S*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [The importance of design in lithium ion battery recycling – a critical review](https://doi.org/10.1039/d0gc02745f) — *battery recycling – a critical review. Product design is an important factor which can control the efficiency and economics of a recycling*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [A Review of Fire and Explosion Hazards in Sustainable Lithium-Ion Battery Recycling Industries](https://doi.org/10.3390/fire9020076) — *However, EOL-LIBs are more prone to thermal runaway due to defects and aging-induced degradation, which can lead to fire and explosion incidents,*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [MnO₂ catalyzed hydrothermal regeneration of spent LiFePO₄ cathode materials for sustainable li](https://doi.org/10.21203/rs.3.rs-10790610/v1) — *lattice repair. Herein, a recyclable MnO₂-catalyzed hydrothermal strategy is proposed for high-value regeneration of degraded LFP cathodes. Integrated hydrothermal treatment with Li₃PO₄@MnO₂*; Europe PMC abstract from broadened search, not full-text verification.

**Potential reusable piece:** [lingrany/EverBatt-LFP-Recycling-Analysis](https://github.com/lingrany/EverBatt-LFP-Recycling-Analysis) — model_candidate_only. README evidence: *[**中文文档 → 新手完全指南.md**](新手完全指南.md)  Python implementation of **Techno-Economic Analysis (TEA)** and **Life Cycle Assessment (LCA)** for LFP (LiFePO₄) battery recycling, based on*.

**Unresolved:** Model inputs, LFP chemistry, permit/safety compliance and economics must be recalibrated independently; its published model output is not operator profit evidence.; code rights and commercial demand not reviewed.

---

## Food Redistribution Outcomes

**Observed or documented problem (source-bounded):** Food redistribution programs often measure recovered kilograms or pickup performance while actual beneficiary nutritional and net lifecycle benefits remain insufficiently linked to real operations.

**Mechanism being investigated:** Redistribution changes supply-chain routing, storage energy, spoilage and beneficiary access; causal and environmental effects depend on which food would otherwise be wasted or purchased.

**Required capability contract:** Time-bounded donor/recipient availability, verified pickup and temperature history plus outcomes and LCA-ready operational records.

**Falsifying/decisive measurement:** Trace a sample donation from origin to recipient, determine actual consumption/spoilage and measure transport/energy costs for a counterfactual comparison.

**Original-source context and limitations:**

- [Exploring the Role of Social Supermarkets in Addressing Food Insecurity and Food Waste: A Scop](https://doi.org/10.1111/nbu.70053) — *Exploring the Role of Social Supermarkets in Addressing Food Insecurity and Food Waste: A Scoping Review.. Tackling food insecurity and food waste*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

- [Comparing the Environmental Impacts of Representative Food Donation and Redistribution Strateg](https://doi.org/10.3390/foods15040645) — *configurations and operational management options, using 391.8 kg of redistributed food over two weeks as the functional unit. Each of the eight*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

- [Smart Food Waste Rescue Hub Application: IOT-Enabled Platform for Surplus Food Redistribution](https://doi.org/10.55041/ijsmt.v2i5.132) — *of an ESP32 microcontroller equipped with DHT22 temperature/humidity sensors and MQ-series gas sensors, which continuously monitor environmental conditions during food storage and*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [Eating waste : a critical evaluation of surplus food redistribution as solution to food waste ](https://openalex.org/W2906684235) — *thesis argues that SFR can boost food access and create important spaces of encounter. However, it demonstrates how organisations’ articulations with corporations,*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

**Potential reusable piece:** [openfoodfoundation/openfoodnetwork](https://github.com/openfoodfoundation/openfoodnetwork) — adjacent_distribution_platform. README evidence: *The Open Food Network is an online marketplace for local food. It enables a network of independent online food stores that*.

**Unresolved:** A producer marketplace is not automatically a charity surplus claiming system, traceable food safety process, or beneficiary nutrition study.; code rights and commercial demand not reviewed.

---

## Flood Warning To Impact

**Observed or documented problem (source-bounded):** Flood vulnerability and community early-warning deployments can be documented separately without knowing whether warnings prevented injury, drowning, displacement or service disruption.

**Mechanism being investigated:** Rainfall and water-level forecasts must be translated into geographically appropriate lead times, accessible warnings and practical evacuation/health-facility response.

**Required capability contract:** Location-specific station feeds, forecast uncertainty, alert thresholds, dissemination reliability, response actions, and event-linked health outcomes.

**Falsifying/decisive measurement:** Replay historical water levels against thresholds; assess false alarms, useful lead time, message receipt, evacuation behavior and health-service continuity.

**Original-source context and limitations:**

- [Climate induced flooding exposure among urban residents in Uganda](https://doi.org/10.21203/rs.3.rs-9885849/v1) — *differ, GKMA is primarily affected by rapid-onset flash and pluvial floods, whereas Kasese faces recurrent, longer-lasting riverine floods associated with more severe*; Europe PMC abstract from broadened search, not full-text verification.

- [Climate Change as a Health Security Threat in Pakistan: Preparing Health Systems for Extreme E](https://doi.org/10.5334/aogh.5294) — *more than 26 million people, damaged health infrastructure, disrupted essential services, and placed the country at the top of the Germanwatch Climate*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

- [When floods hit the Ban Kao Many community in Nan District, Luang Prabang Province, Laos, peop](https://www.who.int/news-room/feature-stories/detail/the-importance-of-preparedness--strengthening-community-resilience-against-flash-floods) — *Province, Laos, people were prepared. An early warning system from national agencies helped to forecast the flood. Once the announcement had been*; Selected official-site HTML paragraphs. Not a current local outcome survey or program implementation audit..

- [The Intergovernmental Panel on Climate Change defines floods as “the overflowing of the normal](https://www.who.int/europe/health-topics/floods) — *Floods are the most common form of natural disaster in the European Region, which has experienced in recent years some of the*; Selected official-site HTML paragraphs. Not a current local outcome survey or program implementation audit..

**Potential reusable piece:** [WeixuanZ/flood-warning-system](https://github.com/WeixuanZ/flood-warning-system) — forecast_interface_prototype. README evidence: *src="/docs/search.png" alt="" width=80%> </p>  ### Prediction  High risk stations are displayed, and predicted for future changes in water level.  <p align="center">*.

**Unresolved:** A water-level prediction prototype cannot be treated as a validated local warning network or demonstrated reduction in health harms.; code rights and commercial demand not reviewed.

---

## Classroom Ventilation Outcomes

**Observed or documented problem (source-bounded):** Schools can show high indoor CO₂ and respiratory burden without evidence that a given sensing or ventilation intervention improves clinical outcomes in those classrooms.

**Mechanism being investigated:** CO₂ is primarily an occupancy/ventilation proxy rather than a direct measurement of all particles, molds or pathogens; source exposure and response mechanisms differ.

**Required capability contract:** Calibrated CO₂ logging, time/occupancy metadata and feasible ventilation intervention with parallel PM/filtration and independently measured outcomes.

**Falsifying/decisive measurement:** Check reference-sensor calibration and ventilation states; measure CO₂ and PM changes, then avoid claiming clinical impact absent an adequately designed health evaluation.

**Original-source context and limitations:**

- [Indoor air quality and health in schools](https://doi.org/10.1590/s1806-37132014000300009) — *diseases in children. METHODS: We evaluated 1,019 students at 51 elementary schools in the city of Coimbra, Portugal. We applied a questionnaire*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [School Indoor Air Quality](https://openalex.org/W29580953) — *School Indoor Air Quality. Indoor air quality is affected by emitence of various sources and air movement dynamics. Indoor air pollutants can*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [Asthma Intervention with Residential Ventilation and Air Cleaner (AIRVAC) Study: A 4-arm paral](https://doi.org/10.1371/journal.pone.0358221) — *improve indoor air quality (IAQ); however, clinical evidence on their comparative health impacts remains limited. Therefore, this trial aims to evaluate the*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

**Potential reusable piece:** [ajlongshanks/co2_esphome](https://github.com/ajlongshanks/co2_esphome) — measurement_component_only. README evidence: *2021-07-31 at 3 30 18 PM](https://user-images.githubusercontent.com/78609906/127737056-21c92be9-78cf-49c9-88bf-fd5cdb5c010e.jpeg) A co2 Monitor based on ESP32 with SCD30 sensor  **Board selection:** using lilygo TTGO T-DISPLAY*.

**Unresolved:** A device design measures carbon dioxide and does not automatically quantify health benefits, deliver ventilation remediation, or guarantee reliable institutional calibration.; code rights and commercial demand not reviewed.

---

## Dog Population Identity And Movement

**Observed or documented problem (source-bounded):** Free-roaming dog counts and vaccination campaigns need individual/temporal reconciliation and movement understanding, while program outputs do not alone establish sustained population or rabies effects.

**Mechanism being investigated:** Births, deaths, immigration, ownership changes and observation effort affect apparent abundance; vaccination coverage and campaign effort require distinct denominators.

**Required capability contract:** Repeated geotagged sightings or individual photo IDs linked to survey effort, capture/re-capture assumptions and vaccination/source-control events.

**Falsifying/decisive measurement:** Compare repeated-sighting identity reconciliation against blinded human labels and independent field sampling; check stability and immigration effects.

**Original-source context and limitations:**

- [The demography of free‐roaming dog populations and applications to disease and population cont](https://doi.org/10.1111/1365-2664.12279) — *the contribution of demographic processes (i.e. births, deaths and movement) to variations in dog population size or density, or determined the factors*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [Long-term evaluation of a zoned catch-neuter-vaccinate-release program integrating owner engag](https://doi.org/10.14202/vetworld.2026.2816-2849) — *free-roaming dogs. Materials and methods From 2021 to 2025, sexually intact free-roaming dogs were captured along predefined routes with standardized effort, while*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

- [The vacuum effect in free-roaming dog management: Conceptual foundations, boundary conditions,](https://doi.org/10.1016/j.onehlt.2026.101556) — *The vacuum effect in free-roaming dog management: Conceptual foundations, boundary conditions, and One Health implications.. Management of free-roaming animal populations in human-dominated*; Europe PMC abstract from broadened search, not full-text verification.

- [Population Dynamics of Owned, Free-Roaming Dogs: Implications for Rabies Control](https://doi.org/10.1371/journal.pntd.0004177) — *but maintaining the critical threshold of vaccination coverage for herd immunity in these populations is hampered by their rapid turnover. Knowledge of*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

**Potential reusable piece:** [kobotoolbox/kpi](https://github.com/kobotoolbox/kpi) — data_capture_infrastructure_only. README evidence: *# KPI  [![Python Build Status](https://github.com/kobotoolbox/kpi/actions/workflows/pytest.yml/badge.svg?branch=main)](https://github.com/kobotoolbox/kpi/actions?query=workflow%3Apytest+branch%3Amain) [![Python Coverage Status](https://coveralls.io/repos/github/kobotoolbox/kpi/badge.svg?branch=main)](https://coveralls.io/github/kobotoolbox/kpi?branch=main) [![JavaScript Build Status](https://github.com/kobotoolbox/kpi/actions/workflows/npm-test.yml/badge.svg?branch=main)](https://github.com/kobotoolbox/kpi/actions?query=workflow%3Anpm-test+branch%3Amain) [![DPG Badge](https://img.shields.io/badge/Verified-DPG-3333AB?logo=data:image/svg%2bxml;base64,PHN2ZyB3aWR0aD0iMzEiIGhlaWdodD0iMzMiIHZpZXdCb3g9IjAgMCAzMSAzMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTE0LjIwMDggMjEuMzY3OEwxMC4xNzM2IDE4LjAxMjRMMTEuNTIxOSAxNi40MDAzTDEzLjk5MjggMTguNDU5TDE5LjYyNjkgMTIuMjExMUwyMS4xOTA5IDEzLjYxNkwxNC4yMDA4IDIxLjM2NzhaTTI0LjYyNDEgOS4zNTEyN0wyNC44MDcxIDMuMDcyOTdMMTguODgxIDUuMTg2NjJMMTUuMzMxNCAtMi4zMzA4MmUtMDVMMTEuNzgyMSA1LjE4NjYyTDUuODU2MDEgMy4wNzI5N0w2LjAzOTA2IDkuMzUxMjdMMCAxMS4xMTc3TDMuODQ1MjEgMTYuMDg5NUwwIDIxLjA2MTJMNi4wMzkwNiAyMi44Mjc3TDUuODU2MDEgMjkuMTA2TDExLjc4MjEgMjYuOTkyM0wxNS4zMzE0IDMyLjE3OUwxOC44ODEgMjYuOTkyM0wyNC44MDcxIDI5LjEwNkwyNC42MjQxIDIyLjgyNzdMMzAuNjYzMSAyMS4wNjEyTDI2LjgxNzYgMTYuMDg5NUwzMC42NjMxIDExLjExNzdMMjQuNjI0MSA5LjM1MTI3WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cg==)](https://digitalpublicgoods.net/r/kobotoolbox)  For production always use a specific release branch,*.

**Unresolved:** KPI project README identifies survey infrastructure but the selected excerpt does not verify animal re-identification, population estimation or legal field deployment.; code rights and commercial demand not reviewed.

---

## Heat Warning To Protective Action

**Observed or documented problem (source-bounded):** Heat mortality projections and early-warning plans are widespread sources of concern, but a meteorological warning is not itself evidence that vulnerable households received or acted on protection.

**Mechanism being investigated:** Heat hazards affect people differently by age, occupation, housing and access to cooling; forecasting only supplies one input to risk communication and response.

**Required capability contract:** Local forecast/historical weather streams plus vulnerability stratification, accessible alerts, cooling access and attributable response records.

**Falsifying/decisive measurement:** Backtest spatial heat-warning thresholds and measure protection reach and subsequent outcomes in defined at-risk groups.

**Original-source context and limitations:**

- [Global, regional and national projections of heatwave-related death burdens under climate chan](https://doi.org/10.1016/j.ebiom.2026.106419) — *adaptation scenarios, were incorporated to estimate excess heatwave-attributable deaths during the 2030s, 2050s, and 2090s, with uncertainty quantified via Monte Carlo simulations.*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

- [Heatwave Early Warning Systems and Adaptation Advice to Reduce Human Health Consequences of He](https://doi.org/10.3390/ijerph8124623) — *Heatwave Early Warning Systems and Adaptation Advice to Reduce Human Health Consequences of Heatwaves. INTRODUCTION: With climate change, there has been an*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [Heat is an important environmental and occupational health hazard. Heat stress is a leading ca](https://www.who.int/news-room/fact-sheets/detail/climate-change-heat-and-health) — *heatwaves by developing heat action plans, heat early warning systems and advisories, and emergency response plans that map the risks, vulnerable populations,*; Selected official-site HTML paragraphs. Not a current local outcome survey or program implementation audit..

- [Urban household adaptation to extreme heatwaves: health impacts, socio-economic disparities an](https://doi.org/10.1007/s43621-024-00697-2) — *to address heatwave vulnerability, particularly among low-income urban households. To enhance heatwave resilience in urban areas, the study proposes sustainable and long-term*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

**Potential reusable piece:** [open-meteo/open-meteo](https://github.com/open-meteo/open-meteo) — weather_data_component_only. README evidence: *curl "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m" ```  ## Features  - [Hourly weather forecast](https://open-meteo.com/en/docs) for up to 16 days - Global weather models with 11 km*.

**Unresolved:** Forecast feeds do not provide vulnerability targeting or health outcomes; hosted API explicitly distinguishes commercial use rights.; code rights and commercial demand not reviewed.

---

## Ewaste Toxicant Control

**Observed or documented problem (source-bounded):** Informal and formal electronic recycling expose workers and communities to metals and flame retardants, while an environmental modeling toolkit cannot replace occupational monitoring or hazard controls.

**Mechanism being investigated:** Thermal/mechanical dismantling disperses dust, volatile compounds and contaminated material streams; exposure depends on process conditions and worker protection.

**Required capability contract:** Site-specific emissions/exposure sampling, traceable process inventories, validated protective measures and comparable environmental impact accounting.

**Falsifying/decisive measurement:** Measure airborne/workplace exposures by process and compare risk controls before and after intervention; distinguish LCA impacts from personal exposure.

**Original-source context and limitations:**

- [Formal recycling of e-waste leads to increased exposure to toxic metals: An occupational expos](https://doi.org/10.1016/j.envint.2014.07.006) — *digestion. The air sampling indicated greater airborne exposure, 10 to 30 times higher, to most metals among the recycling workers handling e-waste*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [Contamination of indoor dust and air by polychlorinated biphenyls and brominated flame retarda](https://doi.org/10.1016/j.envint.2012.11.006) — *and air by polychlorinated biphenyls and brominated flame retardants and relevance of non-dietary exposure in Vietnamese informal e-waste recycling sites. This study*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [E-waste is one of the fastest growing solid waste streams in the world (1).](https://www.who.int/news-room/fact-sheets/detail/electronic-waste-(e-waste)) — *Informal e-waste recycling activities may have several adverse health effects. Children and pregnant women are particularly vulnerable. Children and pregnant women are*; Selected official-site HTML paragraphs. Not a current local outcome survey or program implementation audit..

- [Electronic Waste-Derived Nanomaterials: Environmental Release, Toxicity, and Public Health Ris](https://doi.org/10.3390/nano16140892) — *and biological processes, can transform into nanoscale materials. These electronic waste-derived nanomaterials are increasingly recognized for their potential environmental mobility, bioavailability, and*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

**Potential reusable piece:** [brightway-lca/brightway2](https://github.com/brightway-lca/brightway2) — lifecycle_accounting_adjacent. README evidence: *framework  Brightway2 is a framework for advanced life cycle assessment calculations. It consists of several components which each accomplish specific tasks.*.

**Unresolved:** LCA is a different endpoint from measured worker exposure and does not enforce on-site toxicant controls.; code rights and commercial demand not reviewed.

---

## Gig Worker Algorithmic Harm

**Observed or documented problem (source-bounded):** Food-delivery platforms face reported accident and health risks associated with workload and algorithmic management; no listed software implementation here is independently shown to reduce worker injury.

**Mechanism being investigated:** Automated task assignment and incentives interact with deadline pressure, fatigue, road exposure and worker autonomy; descriptive sentiment data alone cannot isolate causal impacts.

**Required capability contract:** Ethical, privacy-aware assignment/exposure telemetry, labor outcomes with counterfactual evaluation and operator/worker consent.

**Falsifying/decisive measurement:** Define injury/fatigue reporting, verify consent, examine variations in dispatch policies and confounders before alleging causal effect.

**Original-source context and limitations:**

- [Occupational injuries and health risks among food delivery riders in China: research progress ](https://doi.org/10.3389/fpubh.2026.1932962) — *in China, reshaping delivery work through strict deadlines, piece-rate pay, algorithmic management, long working hours, and intensive road exposure. These conditions may*; Europe PMC bibliographic abstract, NOT full-text verification, peer review, or clinical proof.

- [Algorithmic management and app‐work in the gig economy: A research agenda for employment relat](https://doi.org/10.1111/1748-8583.12258) — *Algorithmic management and app‐work in the gig economy: A research agenda for employment relations and HRM. Abstract Current understanding of what constitutes*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [Platform‐Mediated Gig Work and Health: A Scoping Review](https://doi.org/10.1002/ajim.70007) — *and any measure of physical or mental health. We abstracted country, study design, population, sample size, exposure measure, and health outcome. We*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

- [Algorithmic management in the gig economy: A systematic review and research integration](https://doi.org/10.1002/job.2831) — *Algorithmic management in the gig economy: A systematic review and research integration. Summary Rapid growth in the gig economy has been facilitated*; OpenAlex metadata/abstract; not verified full text, causal study or actual program.

**Implementation match:** intentionally unfilled. No credible repo has yet been shown to address the core risk.

---

## Inference boundary

This atlas is an evidence-aligned investigative worklist, not independent human semantic adjudication or a causal study. Research sources include preprints, abstracts and official-site material. Broad source claims must not be generalized across populations/geographies; designs and trial protocols are not positive outcomes. No implied paid procurement, current license grant, or proven deployment.

The next meaningful mapping pass should compare these capability contracts with multiple alternative implementations per mechanism, inspect actual APIs/engineering tests, and attach independent operator cost/demand evidence. Do not rank, select or pitch opportunities from this map alone.
