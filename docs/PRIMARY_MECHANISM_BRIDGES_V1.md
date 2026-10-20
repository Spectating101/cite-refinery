# Primary-source problem-mechanism bridges — meaningful connections, not more topic tags

21 October 2026. Draft follow-up to Cite–Refinery #75.

## What we changed

Previous work connected public GitHub repository descriptions with institutional procurement descriptions. The academic layer did not attach credibly: **zero** scientific context links survived that particular 17-relationship procurement comparison. Adding generic academic citations would have created false authority.

This pass starts from **operating problems and their mechanisms** instead of contract titles or GitHub tags. An investigator authored eight bounded problem/capability contracts across materials recycling, food logistics, floods, classroom air, roaming dogs, heat, e-waste exposure and platform-worker health. These are explicitly hypotheses.

The extractor loaded the authorized original **63-source development corpus**. For each selected source it confirmed both source identity and SHA-256 against the earlier source map, and retained an exact quote of at most 22 words. The release includes only 31 bounded source references/excerpts, **not** the original full-text private dump. Previously generated AI summaries were not treated as source proof.

We then identified seven reusable OSS candidates and independently fetched each upstream README. The recorded Git blob SHA and literal capability excerpt were checked against the downloaded README. The selected candidates are functional *components or adjacent implementations*, not validated solutions.

## The substantive interpretations

**Battery recycling.** Papers about route economics, battery pack design, fire hazards and LFP cathode regeneration describe different stages of one difficult process. An [EverBatt-inspired LFP techno-economic model](https://github.com/lingrany/EverBatt-LFP-Recycling-Analysis) offers a possible scenario tool—not evidence that a local LFP plant can be profitable or safe. The missing engineering contract combines uncertain throughput, transportation, feedstock chemistry, hazard controls and saleable output. A favorable modeled margin without these assumptions is not an arbitrage margin.

**Food redistribution.** The food LCA paper evaluates environmental outcomes under specified redistribution scenarios; an independent IoT pilot *reports* kilograms rescued and faster pickups; social supermarket research documents a different institutional role. [Open Food Network](https://github.com/openfoodfoundation/openfoodnetwork) could help with producer/distribution sales workflows, but that does not verify safe time-bound rescue, actual consumption or a net environmental impact. These studies cannot automatically validate each other's outcomes.

**Flood response.** An Uganda study distinguishes flash/pluvial from longer-lasting riverine flood exposures. Pakistan material describes health-facility stresses; a WHO feature describes warning arrangements in Laos. The [flood-warning-system](https://github.com/WeixuanZ/flood-warning-system) README covers water-level station monitoring and prediction, but not local evacuation reliability, health outcomes or public-authority authorization. A defensible result would require warning lead-time and response-to-outcome tracking.

**Classroom ventilation.** An empirical school study reports CO₂ conditions and respiratory associations, while an unrelated AIRVAC paper describes an intervention trial *protocol*, not a positive result. A [CO₂ ESPHome sensor project](https://github.com/ajlongshanks/co2_esphome) may facilitate measurement. It is not automatically a clinical intervention, ventilation remediation or calibrated school instrument.

**Roaming dogs.** Population change depends on births, deaths, immigration and observation effort, while a zoned CNVR study reports campaign experience. [KoboToolbox KPI](https://github.com/kobotoolbox/kpi) is possible survey infrastructure but the selected README does not verify individual re-identification. The missing steps are repeatable identity reconciliation and population-estimation model validation. The previously reviewed Taiwan dog source graph may be joined only after matching survey methods and scope.

**Heat.** A mortality projection and heat warning guidance describe vulnerability and protective actions, not a demonstrated causal benefit of weather APIs. [Open-Meteo](https://github.com/open-meteo/open-meteo) provides forecast/historical data streams, not identified vulnerable people or proof of protection; hosted usage has separate commercial terms. Build an explanation of the pathway from forecast to actual protective behavior before considering a service.

**E-waste toxicants.** Formal recycling exposure studies report measured metal exposure, other sources discuss informal waste and flame retardants. [Brightway2](https://github.com/brightway-lca/brightway2) could help environmental impact accounting but is not a substitute for personal air sampling, biological exposure measures or safety controls.

**Gig-worker harm.** Research describes mechanisms involving deadline pressure, fatigue and algorithmic control. No verified OSS intervention candidate is linked; the missing implementation is left **unfilled**, not falsely filled with a social monitoring tool.

## A more important discovery than counts

Six of the seven mechanism-relevant repository identities did **not** appear in our earlier 1,287-repository, topic-based search sample. That does not establish novelty, market absence or underconversion. It establishes **a search coverage failure**: a problem-driven query surfaced software that topic-based sampling missed.

The combined graph now contains two tracks: primary source → interpreted mechanism → optional README-based technical component, and published institutional requirement → proposed implementation. There is **no exact overlap** between the seven problem-driven repo identities and the previously linked institutional-need repo identities. The merger explicitly creates zero speculative cross-track edges.

The correct next move is therefore not to claim a completed three-layer stack; it is to search from each defined mechanism into additional independently documented implementations and actual operating/institutional needs, then validate function, geography, legal rights and economic evidence.

## Evidence boundaries and proof of work

- Eight manually framed operational mechanisms, 31 distinct original-source identities, seven checked README blobs.
- Seven component/adjacent technical leads, one intentionally unfilled implementation category.
- No code from third-party projects deployed or executed; no real-world effectiveness established.
- No license, maintainer permission, buyer intent, current tender eligibility, or captured surplus established.
- Frozen corpus split and private holdout from #70 remain untouched.
- All committed research snippets are bounded original-source quotations rather than copies of full research materials.

See the [readable mechanism atlas](../research_materials/opportunity_atlas/PRIMARY_MECHANISM_ATLAS.md), [typed mechanism graph](../research_materials/opportunity_atlas/primary_mechanism_network.json), [merged provenance gap view](../research_materials/opportunity_atlas/INTEGRATED_GAPS.md) and [merged graph](../research_materials/opportunity_atlas/integrated_evidence_graph.json).

The next milestone is **source-mechanism-equivalent** relationships spanning actual operator observations, technical implementations and organizations' declared needs—not a leaderboard of enticing repositories.
