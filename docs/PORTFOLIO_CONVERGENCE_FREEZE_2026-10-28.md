# Portfolio Convergence Freeze — Solo-Directed Research & Engineering Lab
**Date:** 2026-10-28  
**Status:** Design / experiment protocol freeze only; NOT an implemented end-to-end product, physical release, procurement approval, public allegation, token issuance, or production deployment.  
**Owner of this memo:** Cite–Refinery / Atlas as *coordination reference*, not an exclusive runtime or replacement for project owners.

## 0. Decision and central thesis
The portfolio should be treated as independently useful, inter-operable capabilities—not a race to sell every repository as a separate SaaS, nor an excuse to create a giant monolith.

The intended closed loop:
1. **Discover** practical problems, scholarly mechanisms, available methods, implementation candidates and uncertainty (Atlas = Practical/Nocturnal + Academic/Cite + Program/Refinery; Cite-Agent remains separate).
2. **Acquire** original data and evidence with recoverable, provenance-preserving collection (Research Drive, with source rights respected).
3. **Compose / implement** using owned engineering modules *and* licensed existing software (Hardware Splicer, engineering/CAD/firmware toolchains, specialist models).
4. **Evaluate** technical, scientific and real-world assertions against independent tests (Policy Lab, domain-specific verification).
5. **Decide / convert** using actual economic, adoption, research and funding outcomes, not promises (HS commercial decisions, Sharpe–Terminus where useful, Gauntlet–Blowback; Solarpunk as an optional downstream research framework).
6. **Feedback** verified results, negative outcomes, new capabilities and limitations into Atlas without silently rewriting historical evidence.

**Initial flagship experiment:** Atlas + Research Drive + Hardware Splicer -> Policy Lab / Solarpunk **Energy Evidence Challenge 001**. This is a use case and falsifiable integration benchmark, *not* proof of an energy-backed asset or a new energy source.

## 1. Separate domains and authority boundaries
| Domain | Existing owner / role | Outputs | Cannot authorize |
| --- | --- | --- | --- |
| Atlas Practical | Nocturnal | Source-bound practical observations, legal/event hypotheses, case provenance, editorial packets | Accusations, publication, subject contact without its independent review gate |
| Atlas Academic | Cite, Cite-Agent | Papers, claims, mechanisms, limits and cited findings | Unchecked generalizations, automatically promoted scholarly consensus |
| Atlas Program | Refinery | Tools, implementations, specifications, capabilities, gaps, tests | Real-world suitability merely from repo/demo existence |
| Data acquisition | Research Drive | Publisher-bound original records, schemas, dataset receipts and download artifacts | Intellectual property/use rights it does not hold, scientific interpretation from file integrity |
| Engineering | Hardware Splicer, specialist external tools | Designs, firmware, simulation, CAD, material and measurement plans, build artifacts | Physical safety, functional performance or manufacturability from software CI alone |
| Energy assessment | Policy Lab | Domain policy, model/measurement comparisons, uncertainty and review decisions | Claims supported only by simulation, uncalibrated equipment or unverifiable provenance |
| Energy/economic research | Solarpunk | Conditional valuation/accounting/contract experiments | Financial issuance, energy ownership or legal rights absent independent authorization |
| Capital and conversion | Sharpe–Terminus / Gauntlet / HS commercial | Cost estimates, capital options, potential buyers, funders, delivered outcomes | Revenue without settlement evidence or investment commitments without consent |

A capability may be reused outside its native project without surrendering this separation of authority.

## 2. Absorb-or-build rule (frozen)
**Existing capability is an asset to investigate, not automatically a competitive threat.** Choose per component:
- **Adopt:** use an existing verified tool.
- **Absorb:** integrate through an adapter while preserving licenses, input/output identity, version and attribution.
- **Fork/extend:** only with compatible license, maintainable ownership and a measurable adaptation need.
- **Reimplement:** if justified by independence, domain-specific constraints, safety/evidence needs, cost or architecture.
- **Keep parallel implementations:** where genuinely independent methods improve falsification and error detection.
- **Retire/park:** when total lifecycle cost exceeds any demonstrated unique contribution.

The capability graph models functions, requirements, test evidence, dependencies, implementations and legal/operational constraints. A repository is one container of capabilities, not the atomic unit of evaluation. Do not claim that connected models using shared data or shared assumptions constitute independent corroboration.

## 3. Shared evidence contract (proposal, not an existing universal schema)
Each cross-project exchange SHOULD carry a portable **evidence envelope** with the following categories. Native schemas remain authoritative inside owning projects; adapters convert and log loss of information.

**Required:** envelope/schema version; producer identity and repository/ref/version; produced timestamp and time zone; artifact type and immutable digest; source locator/rights classification; transformation/runtime identity; input artifact digests; claim/measurement scope; verification method and result; uncertainty/known limitations; owner/review state; permitted downstream operations; correlation/run ID and reproducibility instructions.

**Optional:** physical instrument identity/calibration and method independence; measured units and intervals; model or software versions; economic currency/quote-vs-hypothesis-vs-settled status; customer consent; restricted evidence references (never place sensitive payloads directly into a public index).

Receipts must distinguish **observed**, **computed**, **inferred**, **simulated**, **proposed**, **independently measured**, **third-party attested**, **financially settled**, **rejected**, and **unverified** evidence. These are not a single ordinal "truth" score. Exact byte hashes verify integrity, not scientific correctness.

Possible alignment: W3C PROV-compatible entities/activities/agents, while preserving each project's original data model.

## 4. Cross-project operational handoffs
1. Atlas emits a candidate problem / mechanism / implementation *with specific references, confidence limits and unresolved questions*. The headless inbox from Cite–Refinery PR #130 is a **local snapshot-change interface only**, not a live autonomous source discovery or publication authority.
2. Research Drive resolves a bounded data request only under owner and source permission; returns immutable original bytes, normalization instructions, transformations, collection date and independent source-cell checks.
3. Refinery maps reusable technical candidates and implementation constraints; records upstream licenses, maintainers, platform compatibility, dependency and benchmark coverage.
4. HS accepts a scoped design requirement and approved input references, then produces design / firmware / CAD / simulation artifacts plus a test ledger. Compile success and watertight solids stay separate from physical performance and safe deployment.
5. Policy Lab independently adjudicates energy claims with pinned policies, traceable inputs, relevant physics/measurement checks, and explicit **HOLD/BLOCK** outcomes. It cannot be overridden by a favorable Atlas or HS rating.
6. Downstream cost/market layers can consume verified outputs but may not upgrade data quality, physical readiness, or revenue evidence.

**Minimum cross-repo interfaces:** a versioned portable JSON packet + artifact pointers, a read-only capability descriptor, and a result/evaluation packet. Choose CLI/MCP/batch by actual operational need; do not require a new web UI or shared database.

## 5. Flagship: Energy Evidence Challenge 001 (three increasingly demanding gates)
**Question:** Does the combined pipeline produce an independently reproducible and better-evidenced assessment of a real energy-system claim compared with strong off-the-shelf and separate-component baselines?

### E0 — Source-grounded offline replay
- Pick one publisher-pinned PV production/performance dataset and one deliberately difficult negative/control case from Policy Lab's E7 lineage.
- Atlas supplies published mechanisms and candidate methods. Research Drive independently collects source-licensed data and receipts (when permitted). HS produces an instrumentation / software / model plan without inventing measurements.
- Policy Lab replays the relevant E7 canonical decision/constraint system, preserves blocked results and compares against the unchanged precommitted external references.
- Accept only if all material source identities and numeric fields are traceable, units/time zones coherent, no false support is asserted and negative results remain negative.
- Existing E7 evidence includes a conditional PVDAQ success and a **failed** external-weather holdout; these must not be rewritten as universally predictive models.

### E1 — Isolated DC metrology
- Follow Solarpunk PLRS-5's pre-frozen **24V nominal / max 120W / isolated current-limited laboratory supply**, *no battery or grid*, with appropriate qualified safety review.
- Use the planned INA228 path only as a candidate logger. Obtain actual instrument serial/calibration records, true independent method/reference, shunt and time-base uncertainty, protocol and custody evidence.
- HS can prepare firmware, enclosure, acquisition software, wiring/PCB proposals and independent simulations; physical hardware must be built and tested separately with appropriate oversight.
- Precommit error-injection, missing-data, channel-swap, clock-drift and cross-logger tests. Report actual uncertainty and failures. **Simulated sensor gates do not imply metrological accuracy.**
- No real run is authorized by this freeze. Do not claim PV generation because a bench supply delivered power.

### E2 — Energy-generation claim adjudication
- Only after E1 succeeds, evaluate a genuinely independently metered generation source with qualified source custody, measured electrical quantities, site conditions, timestamps, baseline and uncertainty.
- Apply relevant PV-monitoring and measurement standards as appropriate to the use case. Independently audit claims before any economic interpretation.
- **No issuance, energy asset backing, yield guarantee, grid export or legal right is inferred** from a successful software/bench test. Those remain separate regulatory, contractual, ownership and independent-verification questions.

## 6. Evaluation protocol (do not evaluate the integrated system against a straw man)
**Arms:** A. strong general-purpose frontier agent with appropriate existing tools; B. separate portfolio components with manual handoffs; C. integrated envelope/adapter workflow. Same task definition, permitted source access, budget, actual hardware, and external grading.

**Measurements:** correct factual/quantitative outputs; independently verified source/claim coverage; capability and design feasibility; negative-control/failure detection; human intervention and elapsed time; acquisition/inference/infrastructure and specialist labor cost; provenance completeness; physical quality and safety (where physically tested); repeatability and maintenance cost; adoption or paid external outcome.

Pre-register held-out cases and acceptance criteria before changing the system. Preserve unsuccessful runs. Prevent answer leakage, baseline handicaps, unlicensed dataset access and tests that mistake replay for new data collection. Prefer independent external reviewers for physical and scientific evidence.

**Go/no-go:** expand integration only if C has a measurable, repeatable advantage or unique verified capability worth its incremental costs. Otherwise reuse A or B, narrow the integration, and keep the engines independent.

## 7. Two non-energy transfer benchmarks
- **Technology Conversion Challenge:** find a documented demand/problem + an underutilized capability, verify suppliers/rights/market, create a narrowly bounded engineering deliverable and seek outside acceptance. Quote, inventory, shipping, tax, labor, repairs and warranty costs must be independently checked; hypothetical margin != revenue.
- **Research-to-Implementation Challenge:** source-bound research mechanism -> known open implementation -> experimental protocol -> artifact/test -> limitations -> updated practical/academic/program map. Compare against capable standalone agent and existing open-source workflows.

These are transfer tests. Passing Energy Challenge alone does not establish a general autonomous research engineer.

## 8. Current evidence inventory, as of freeze
- **Cite–Refinery:** three-layer Atlas and existing `cross_layer_stack`; PR #130 has a headless finite-run inbox with synthetic multi-domain replay and focused CI. No unattended live Optiplex schedule or universal adapters verified.
- **Hardware Splicer:** PR #229 has confirmed prior-sha host/ESP32 target compilation and OpenSCAD enclosure geometry. No board flashed, calibrated sensor, physical assembly/thermal test, or verified manufactured unit. PR #214's commercial screening CI passed, with no verified customer payment.
- **Policy Lab:** Solarpunk-coin PR #115 contains E7 energy evidence assessment and retained unsuccessful physical-model holdouts, still draft.
- **Solarpunk:** PR #141 contains instrumentation design and synthetic gating, with **physical-ready = false**. No hardware procurement, calibration or issuance authorization.
- **Research Drive:** draft procurement and source-checking backend has exercised real member dataset collection; no claim of deployed integrated portfolio service or universal source coverage.
- **Nocturnal:** guarded investigative review architecture under draft PR #113, with independent editorial controls and full-environment acceptance outstanding.
- **Gauntlet, Sharpe:** candidate downstream conversion/decision contributors, not assumed to be deployed shared services.

## 9. Sequencing and stop rules
**Stage 0: Freeze** — This memo and later compatible machine-readable task manifests. NO changes to owning repositories and no claims of integration merely from this document.

**Stage 1: Audit** — Exact repo, branch, PR and evidence inventory, rights/licensing and control boundaries. Identify one existing working input/output per project; reject invented adapter contracts.

**Stage 2: Two-system handshake** — First Atlas-to-Research-Drive or Atlas-to-HS scoped packet, with independent integrity replay and no authority elevation.

**Stage 3: Offline energy rehearsal** — E0 using pinned original sources and Policy Lab decisions. Explicitly measure baseline delta and cost.

**Stage 4: Physical bench** — E1 only after safety, equipment, calibration, separate-method review and hardware procurement authorization.

**Stage 5: Transfer test & external review** — One different domain, independent expert grading, and genuine external-use demand.

**Stage 6: Scale selectively** — Only validated paths, sustainable ownership/cost, reproducible results and permissions. Do not merge codebases by default.

Stop building new integration layers if they cannot survive a realistic end-to-end task or if another maintained tool wins the same test more cheaply. An unattractive business case or rejected scientific claim is a legitimate and useful output.

## 10. Non-goals and standing safeguards
- No new universal monolith, automatic merger of repositories, forced GUI, or always-on paid LLM loop.
- No automatic accusation or publication from Nocturnal and no cross-context promotion of sensitive investigative data.
- No purchase, financial commitment, arbitrary remote code execution or physical activation without dedicated approval.
- No real-world energy, metrological precision, safety or token-backing claim from simulated results, model accuracy, source hashes or CI.
- No commercial "conversion" claim without external adoption and evidence of economically realized value.
- No dependence on a single vendor, model, retrieval service or external license where practical.

## 11. Linked implementation evidence (not endorsement or new authority)
- Atlas README and three-layer semantic map: https://github.com/Spectating101/cite-refinery
- Headless inbox: https://github.com/Spectating101/cite-refinery/pull/130
- HS cross-domain generated firmware / enclosure: https://github.com/Spectating101/hardware-splicer/pull/229
- HS commercial screening: https://github.com/Spectating101/hardware-splicer/pull/214
- Policy Lab E7: https://github.com/Spectating101/solarpunk-coin/pull/115
- Solarpunk PLRS-5 instrumentation: https://github.com/Spectating101/solarpunk-coin/pull/141
- Nocturnal guarded research: https://github.com/Spectating101/nocturnal-oversight/pull/113

*Research Drive's private implementation links are deliberately omitted from this public-facing freeze. Its owner may publish a sanitized capability contract separately.*

## 12. Freeze summary
**The portfolio-wide differentiator to test is reproducible conversion from discovered knowledge and existing capabilities into externally reviewable scientific, engineering or economic outcomes.** No novelty, autonomy, physical readiness, general superiority, or sustainable revenue is asserted by design alone.

This is the research protocol and positioning baseline. Amendments require a new dated delta, with explicit changed assumptions and evidence—not retroactive edits that obscure failed or unvalidated work.
