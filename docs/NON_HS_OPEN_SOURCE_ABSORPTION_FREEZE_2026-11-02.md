# Non-HS Open-Source Absorption Freeze — Policy Lab, Nocturnal, Research Drive, Cite-Agent, Atlas and Conversion

**Frozen:** 2026-11-02 (Asia/Taipei)  
**Status:** Research/decision freeze only. No dependencies installed, integrations executed, project branches modified, workflows deployed, sources collected, or release permissions granted.  
**Coordinator:** Cite–Refinery / Atlas, as a public *research reference only*; source-project owners keep their own runtime, evidence and approval boundaries.  
**Relationship:** Specialized annex to [Portfolio Convergence Freeze PR #134](https://github.com/Spectating101/cite-refinery/pull/134) and the existing Atlas headless project-steering work [PR #130](https://github.com/Spectating101/cite-refinery/pull/130). **Not** a replacement, an update to PR #134, or a universal shared runtime.

## 1. Decision being frozen

Scout existing upstream open-source implementations and objectively test whether **reuse** improves existing non-Hardware-Splicer projects. Prioritize correction of known weak tasks (scientific QA, volatile-source preservation, claim grounding, document extraction) over installing trending repositories.

The repo list below records **candidates, not adopted dependencies**. Their README/API descriptions are upstream claims, not measured gains in our projects. Do not interpret relative priority as authorization to start implementation.

| Wave | Host project | Candidate / source | Proposed role | First falsifiable test | Disposition |
| --- | --- | --- | --- | --- | --- |
| P1 | Nocturnal | [Bellingcat Auto Archiver](https://github.com/bellingcat/auto-archiver) | Permitted public-source capture and preservation | Capture frozen public test URLs; verify actual acquired bytes, timestamps, outcome and journal linkage; retain failed captures | **Benchmark first** |
| P1 | Nocturnal | [FileGrail](https://github.com/osintshifu/filegrail) | Local read-only file metadata and provenance examination | Compare file-specific metadata/pivots against known fixtures; report contradictions without asserting authenticity | **Benchmark first** |
| P1 | Policy Lab | [PVAnalytics](https://github.com/pvlib/pvanalytics) | Independent PV time-series QA / flags | Replay approved public time-series with seeded gaps, clock shifts, impossible values, clipping; compare domain judgments and false positives | **Benchmark first** |
| P1 | Policy Lab | [pvlib-python](https://github.com/pvlib/pvlib-python) | Physics/modeling baseline | Reproduce independent weather/solar expected-output analysis; distinguish modeled from metered claims; quantify model sensitivity | **Benchmark first** |
| P1 | Cite-Agent | [PaperQA2](https://github.com/Future-House/paper-qa) | Independent scientific retrieval and claim support baseline | Re-run existing held-out claim set including supported, contradicted, unsupported and wrong-quote cases; exact-page evidence, abstention, cost | **Benchmark first** |
| P2 | Research Drive | [Docling](https://github.com/docling-project/docling) | Layout-aware document/table extraction | Blind original-cell and source-page accuracy across mixed PDF layouts and tables; compare to existing pipeline | Compare |
| P2 | Research Drive / Policy Lab | [Frictionless](https://github.com/frictionlessdata/frictionless-py) | Typed tabular validation, metadata and error diagnostics | Preserve immutable original bytes; identify malformed schema/units/missingness without silently changing rows | Compare |
| P2 | Research Drive / Policy Lab / Cite | [RO-Crate Python](https://github.com/ResearchObject/ro-crate-py) | Interoperable portable evidence package | Export then re-import one rights-aware source+transform+result dossier with no lost hashes, permissions or caveats | Prototype |
| P2 | Nocturnal / Atlas Practical | [OpenAleph](https://github.com/openaleph/openaleph) | Established document/entity investigation and FollowTheMoney interoperability | Import/export an approved fictional or public case; identity/relationship preservation and no unsupported linkage promotion | Compare |
| P2 | Nocturnal | [forenix-oss](https://github.com/thunderstornX/forenix-oss) | Case-history, cryptographic ledger and reviewed-change architecture reference | Compare its case-custody model to native journal; reject any claim that hash chains independently establish truth | Reference / compare |
| P2 | Cite-Agent / Atlas Academic | [PaperSnitch](https://github.com/AImageLab-zip/paper-snitch) | Research-reproducibility review baseline | Grade a frozen small corpus with missing code/data; compare to independently reviewed artifact checklist and calibration | Compare |
| P3 | Atlas | [Repowise](https://github.com/repowise-dev/repowise) | Repository dependency/change-impact reference | Compare held-out dependency questions against existing project registry and manual ground truth; assess license before reuse | Optional |
| P3 | All agent-backed projects | [Cloudflare Security Audit Skill](https://github.com/cloudflare/security-audit-skill) | Independent structured audit technique | Replay authorized, isolated known-positive/negative fixtures; verify finding citations and nonconfirmation of unresolved issues | Optional |
| P3 | Sharpe–Terminus / Research Drive | [OpenBB](https://github.com/openbq-org/OpenBB) | External financial-data interface reference | Evaluate provider rights, point-in-time coverage, adjusted history, revisions and costs; not trading permission | Optional |

**Gauntlet:** ESCO skill normalization is worth considering, but the specific previously suggested repository `Datalab-AUTH/esco-skill-extractor` could not be verified at the checked GitHub path. **Do not register it as an integration** until an actual maintained repository and rights are verified. Use Gauntlet's already-present ESCO work as the baseline.

**Source corrections at freeze:** `NREL/rdtools` currently resolves to [NatLabRockies/rdtools](https://github.com/NatLabRockies/rdtools); `ResearchObject/ro-crate-py` is the verified RO-Crate Python repository; the checked OpenBB repository resolves to [openbq-org/OpenBB](https://github.com/openbq-org/OpenBB). Upstream redirects/organization changes should be preserved and rechecked when pinning commits. These are repository-discovery observations, not integration validation.

## 2. First acceptance wave: three bounded experiments

**N1 — Nocturnal evidence-custody parity.** Use **Auto Archiver + FileGrail**, but evaluate each independently before composing them. Corpus: permitted public stable/volatile URLs and synthetic files with planted metadata conflicts. Grade capture completeness, immutable bytes, journal/quote references, retrieval failure disclosure, access restrictions and source-to-claim separation. No automatic allegations or publication. Archive and metadata observations are **evidence about artifacts**, not automatic proof of events or identities.

**P1 — Policy Lab scientific parity.** Start with PVAnalytics and optionally pvlib on licensed/published PV/inverter measurements already represented in Policy Lab's research set; include withheld and corrupted controls. Grade independent QC, units, alignment, false admission, false rejection and effect on unchanged Policy Lab decisions. Instrument readings and utility provenance remain unverified unless independently authenticated. Do not infer source rights, renewable generation certification, token issuance or energy ownership.

**C1 — Cite-Agent claim-grounding rescue.** Run PaperQA2 against the existing frozen Cite-Agent claim-grounding failures, using equal exact source access, inference budgets and a strong baseline agent. Grade support/contradiction/abstention, correct quotation locations, false positives, human review, cost, and preservation of originals. **Do not reactivate the older public/multi-user product**; any security remediation and product decision remain independent.

## 3. Subsequent evaluation wave

- **Research Drive:** Docling on independently cell-checked original PDFs; Frictionless on tabular integrity; RO-Crate metadata-level compatibility. None may alter original values or turn freshness into historical coverage.
- **Atlas / Nocturnal:** OpenAleph and forenix as reference implementations, not as replacements for editorial authority or the native provenance graph; use fictional/public source-bounded cases.
- **Cite / Atlas Academic:** PaperSnitch as a reproducibility *screen*, not an autonomous peer-review verdict.
- **Gauntlet / Sharpe:** Existing ESCO and the OpenBB provider interface only after the research use case, source rights and need are verified. Keep trading actions and financial conclusions out of this freeze.

## 4. Trial method and admission rule

For each candidate:

1. Verify current owner/repository, latest upstream commit or immutable release, license obligations, permission/security posture, runtime requirements and known limits. Record exact pin, not floating `main` or `latest`.
2. Identify the **specific preexisting native implementation** and the smallest task where upstream might help. Prefer a read-only sidecar or CLI; no monolithic replacement.
3. Pre-register independent ground truth, held-out positive/negative cases and baseline arms: existing owner implementation, suitable external candidate, capable general agent if relevant, and combined implementation only if necessary.
4. Run in sandbox with no private credentials/external contacts and no unrestricted execution; preserve raw source and original validation receipts.
5. Measure correct result, false positives, false negatives, abstentions, rights/provenance fidelity, latency, token/infrastructure cost, operational complexity and maintenance burden.
6. Record one of: `ADOPT`, `ADAPT`, `REFERENCE`, `WATCH`, `REJECT`, `INSUFFICIENT_EVIDENCE`. A `BENCHMARK_FIRST` row is **not** an admission decision. If parity at higher total cost, favor existing native implementation.
7. Never silently upgrade a repository README, GitHub popularity, generated report, deterministic hash or CI pass into proof of empirical/scientific/operational superiority.

**Evidence contract (proposed):** host project; candidate; source URL; upstream commit+license; local evaluated SHA; cases and baseline versions; permitted source IDs; outputs and exact digests; evaluator/independence; measured costs; failed cases; decision rationale; authority restrictions. Preserve producer-specific native schemas. Reusable Atlas registry entries are read-only until independently accepted by their owner.

## 5. Stop and ownership boundaries

- This freeze authorizes **documentation only**, with **zero** execution against private production repositories or source systems.
- No installs, agent runs, schedules, new accounts, site scraping, purchases, merges, releases, security scans of third-party targets, evidence publication, access-control changes, financial trading, or model/measurement claim promotions.
- No direct private repo paths, credentials, source data or security-sensitive details are to be copied into this *public* Atlas coordination document.
- Policy Lab independently owns scientific and physical judgments. Nocturnal independently owns investigative claims/editorial publication. Research Drive owns acquisition/source-rights checks. Cite-Agent owns scholarly verification. Gauntlet/Sharpe maintain separate conversion and financial authority.
- Stop any candidate when its legal/security/operational integration cost exceeds measurable benefit, when it duplicates a stable native capability without improvement, or when unavailable source rights prevent a fair comparison.

## 6. Resume trigger and deliverables

**Frozen until an explicit instruction to resume.** When resumed, begin with one small, read-only benchmark at a time (recommended N1 / P1 / C1). First produce a pinned candidate version + precommitted acceptance fixture; then an exact execution receipt, a comparative result table, and a project-owner decision. Do not convert this plan automatically into a new PR stack.

**At freeze:** No third-party integration outcomes have been measured in this work. This document registers *hypotheses and experiments*, not deployed features or achieved parity.
