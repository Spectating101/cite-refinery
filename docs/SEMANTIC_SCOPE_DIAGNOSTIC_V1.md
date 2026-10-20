# Semantic scope and mechanism validation — development pilot
21 October 2026. Draft child of the native three-layer PR #78.

## Why this is substantive

The new three-layer graph can traverse Practical → Academic → Implementation records, but graph connectivity by itself does not demonstrate a scientifically valid mechanism or a working solution. The earlier system had only literal source-quotation checks. This pass asks whether **the claim actually follows from the retrieved source abstract** and whether a mechanism synthesized across several sources is justified.

The scientific materials are retrieved abstracts and official excerpts from Cite–Refinery's original 63-source **development** corpus. The original retrieved text stays on the authorized Optiplex; only minimal quote-limited outputs are committed. No sealed holdout was read. Abstract-level source agreement is not full-paper, independent human or replication validation.

## Two distinct reviews

**A. Atomic-claim diagnostic.** Twenty-four human-authored diagnostic claims across eight unrelated operating-problem families, three each: (1) a narrowly scoped statement that the abstract directly supports; (2) an extrapolated technical/causal/market implication that it does not establish; (3) a direct statement that contradicts the supplied abstract. Exact source identities/SHA-256 and bounded (8–24 word) literal quotes are checked against the original local abstract. The adjudicator sees no investigator/reference labels. A Gemini 3.8 Flash Medium model returned **23/24 agreement** with the investigator-authored labels. There were **zero false accepted entailment** decisions in this constructed sample. This is neither unbiased accuracy, human gold, nor automatic authority.

The sole disagreement was B02: the reference classified “every commercial pack experimentally profitable” as *contradicted*; the model called it *overreach*. Both reject it as supported; the disagreement is over whether a modeled profitability range that includes negative cases explicitly contradicts that compound claim. The result preserves both labels and rationale instead of silently adjudicating the gold as correct.

**B. Aggregate mechanism critique.** A separate prompt supplies the *entire existing Practical problem, proposed Academic mechanism, technical component hypothesis and the original abstracts actually cited for that mechanism*. It asks whether the synthesis is directly entailed, partially supported, unresolved, or contradictory, with literal source evidence, the most consequential unsupported inference and a falsifying next experiment. This is a **second prompt using the same model family**, not an independent scientific panel or an out-of-sample evaluator. All outcomes remain model hypotheses and do not change graph statuses.

The completed second pass assessed all eight synthesized problem mechanisms: **seven partial support, one bounded support (heat)**. Even the heat mechanism's bounded support is NOT evidence that warning systems reduce deaths; that effect remains a separate unverified intervention outcome. The result exposes which pieces of the *combined synthesis* were not entailed by the separate sources. Do not call this 7 failures or one scientific success: the labels are the same model's source-scope judgments, not measured physical or empirical outcomes.

## Real decisions exposed so far

- **Battery recycling:** A regional techno-economic model evaluates routes and sensitivity to wages, transport, design and process. Studies of hazard handling and hydrothermal cathode restoration exist, but those sources together do not quantify *operating profit after safety/compliance overhead and real-world recovery yield*. The model proposes a pilot-informed cost/safety route comparison before asserting arbitrage.
- **Food redistribution:** A scenario-based LCA and food-recovery pilot are not interchangeable outcome estimates. To infer real environmental and nutrition value, the system needs routing, cold-chain/spoilage, actual consumption, and counterfactual food purchasing or disposal data.
- **Flood response:** Flood exposure, warning dissemination and station monitoring can be separately studied without establishing that installing a particular warning product reduces mortality, injuries or health-system disruption. Required evidence includes threshold performance, warning lead time, message reach, protective response and measured outcomes.
- **Classroom indoor air:** The Coimbra study reports lack of concentration association with high CO₂ but no other significant associations. CO₂ logging and ventilation/air cleaning trial protocols do not demonstrate clinical respiratory improvement. Joint occupancy, pollutant, exposure and intervention data are needed.
- **Free-roaming dogs:** Human movement, ownership and demographic change affect population inference; vaccination or sterilization activity cannot be turned into sustained local population effects without individual follow-up, defined denominators and independent field evaluation.
- **Heat:** Vulnerability and forecast inputs are established as different objects. Weather forecasts do not alone imply targeted, received, acted-upon warnings or reduced death; warning reach and behavior require measurement.
- **E-waste exposures:** Swedish recycling workers had higher measured metal exposure than office workers. Life-cycle impact software cannot replace individual exposure, source control or worker-safety intervention evidence.
- **Delivery-rider harms:** The review identifies deadline pressure and fatigue while noting limited longitudinal/intervention evidence. A social monitoring tool or algorithmic theory is not proof of improved worker safety.

## Operational artifacts and authority

The research outputs are three separate and explicitly non-authoritative products:

- An atomic-claim entailment diagnostic, with benchmark disagreement and exact source quote.
- An adversarial cross-source mechanism critique, including the strongest missing inference and decisive test.
- A **three-layer Academic review queue** attached to existing Practical and Academic IDs without promoting any graph edge.

The native graph does not ingest diagnostic verdicts as qualified sources or technically validated implementation links. To upgrade an evidence status it would still require the explicit operator review pathway from #78; independent scientific review and functional testing are still missing.

## Next step that creates value

For each mechanism, use the critic's identified *missing equation, measurement, context or technical behavior* to request precisely targeted evidence or run a reproducible technical test on a relevant repository. Then inspect whether both the scientific and implementation claims hold for the same population/use case. Only after that should the separate conversion/arbitrage assessment evaluate operator needs, legal rights and complete costs. Avoid opportunistic priority rankings derived from model certainty or test volume.
