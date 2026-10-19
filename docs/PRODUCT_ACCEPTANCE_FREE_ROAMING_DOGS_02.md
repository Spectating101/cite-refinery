# Product acceptance case 02 — Taiwan free-roaming dogs

**Existing infrastructure remains frozen** at annotated tag
`infrastructure-v0.24-freeze-20261019`
(commit `798a312958f593c6f773a433b8e1f76e18572283`).
Case 01 (LLM prompt privacy) remains preserved as a distinct acceptance test.

This is the second, **unrelated problem-domain acceptance case** for the
Cite-Refinery clustered Practical / Academic / Program semantic map.
It demonstrates research navigation and evidence boundaries, not a field-ready
dog-management technology or proven policy success.

## Research problem

How can an investigator connect Taiwan's periodically estimated
free-roaming dog population and local replenishment pressures to
peer-reviewed abundance-estimation methods and actual documented
survey/management programs **without** inventing continuous local
population estimates or demonstrated intervention effectiveness?

The previous public dog pilot is retained untouched at
`examples/free_roaming_dog_semantic_pilot.json` with byte SHA256
`c1188fc6265627cdbd9144c61839a4a1a3a5200db719b0170015906891ffb216`.

The source review is frozen separately at
`examples/acceptance_free_roaming_dog_source_review_v1.json`
with byte SHA256
`a3ff46144b1403226ea1431c2607da6fbf5db660e37260911817dea984750131`.

The acceptance runner checks both exact file digests and applies an
explicit, case-specific qualification overlay to a copy of the pilot.
It does **not** edit the original pilot, add generic integration
infrastructure, or automatically assert truth from source co-occurrence.

## Practical layer: real Taiwan evidence

- Ministry of Agriculture, January 20, 2025:
  [2024 national population survey](https://animal.moa.gov.tw/Frontend/News/Detail/N0000000001599),
  estimated 141,584 free-roaming dogs compared with 159,697 in 2022.
  Sampling took place in 739 villages, and the national methodology is a
  periodic photographic survey every two years. **The ministry explicitly
  cautioned the difference was not statistically significant.** A lower
  point estimate is not automatic proof of management effectiveness.
- [Miaoli County, June 24, 2026](https://animal.moa.gov.tw/Frontend/News/Detail/N0000000002313):
  reported approximately 7,400 roaming dogs in the cited 2025 data and
  continuing abandonment, free-roaming ownership and reproduction pressures.
  The local official account does not establish the exact causes of national
  trends.

## Academic layer: method and population dynamics

- Belo et al., 2015, *Population Estimation Methods for Free-Ranging Dogs:
  A Systematic Review*, DOI
  [10.1371/journal.pone.0144830](https://pmc.ncbi.nlm.nih.gov/articles/PMC4684217/).
  Twenty-six reviewed studies illustrated how detection probability,
  identification, recording and population assumptions can undermine
  abundance estimates. This is methodological evidence, not a new
  2024 Taiwan data collection.
- *Effectiveness of the trap-neuter-return method for free-roaming dog
  management in an urban protected area: Wildlife cannot wait*,
  Global Ecology and Conservation, 2024, DOI
  [10.1016/j.gecco.2024.e02990](https://www.sciencedirect.com/science/article/pii/S235198942400194X).
  Shoushan's population modelling predicted high female sterilization could
  theoretically control abundance without replenishment, but approximately
  50–100 annual incoming dogs could significantly undermine this.
  This is a **site-specific camera-trap study and modelling scenario**,
  not a validated nationwide treatment or causal policy evaluation.

## Program layer: what actually exists

- [Talea by the ICAM Coalition](https://www.icam-coalition.org/talea-user-guide/):
  documented app/web service for making, recording, transmitting and
  analysing street surveys. The user guide specifically says **sighting
  records cannot include an animal photograph** (FAQ 5.4). This matters
  because photographic individual matching is one approach used in
  mark–recapture studies. Talea's documented presence is **not** proof of
  a compatible individual-photo workflow or a locally tested continuous
  abundance estimator. We did not run its app or conduct a field survey.
- [Taiwan Ministry of Agriculture 2026 community-management program](https://animal.moa.gov.tw/Frontend/News/Detail/N0000000002234):
  prioritizes hotspots, female-dog population source control and community
  responsibility. It is a source-backed **policy intention**, not a
  measured outcome or causal treatment estimate.

## Exact semantic result (isolated private acceptance project)

| Record type | Count |
| --- | ---: |
| Semantic modules | 4 |
| Modules containing Practical, Academic and Program records | 3 |
| Practical nodes | 3 |
| Academic nodes | 3 |
| Program nodes | 3 |
| Neutral context and outstanding requirement nodes | 6 |
| Total semantic edges | 16 |
| Qualified source/scope relationships | 9 |
| Candidate relationships | 5 |
| Explicit unresolved missing links | 2 |

**Critical missing links:** (a) Talea's lack of sighting photos means
photo-based individual dog reconciliation is not established from its
documentation; (b) no actually executed local population estimator or
integration to intervention feedback is in evidence.

All inherited implicit-asserted links in the original public pilot were
re-reviewed and conservatively converted to candidate or qualified
scope-level relations. No relation in this acceptance case retains
`asserted` status. The original demonstration packet remains unchanged.

The acceptance output is **`ACCEPTED_WITH_OPEN_GAPS`** for
source fidelity and navigable research mapping. It is **not** accepted
as an operational or production dog-management solution.

## Four researcher-navigation questions

The evaluator identifies exact graph/source records required to answer:

1. What did the Ministry estimate for 2024, and was its decline
   statistically significant?
2. Does Talea natively supply dog photographs, individual reconciliation
   and a validated continuous local population estimator?
3. Can the Shoushan open-population model be assumed to prove
   nationwide sterilization effectiveness?
4. Is the Ministry's 2026 management program known to be effective
   based on the linked evidence?

Each answer is deliberately qualified: **no** to unsupported causal,
technical or population-wide inferences. Four tasks are machine-audited
for evidence traceability.

A repeatable headless Chrome smoke opened the real private case in the
existing three-column interface, counted the observability module's
Practical/Academic/Program records (2/2/2), navigated all four source
questions, inspected official and scholarly source links, and found
zero JavaScript page errors.

**Limit:** Automated browser traversal only demonstrates the UI exposes
information and source links. We have NOT conducted a human researcher
usability study, measured comprehension, task time, or user trust.

## Reproduction

From the repository root, on an authorized workstation:

    PYTHONPATH=src:. python3 scripts/acceptance_free_roaming_dogs.py --db /tmp/NEW-dog-acceptance.sqlite3

The runner refuses pre-existing databases, creates a fresh isolated tenant
and source-reviewed packet, uses existing local private-workspace
review/queue/transaction worker under program control and evaluates the
result. It does not publish data or touch the static Vercel demonstration.

Headless local browser audit (requires Chrome and Playwright):

    PYTHONPATH=src:. python3 scripts/smoke_acceptance_free_roaming_dogs_browser.py

Regression tests:

    PYTHONPATH=src:. python3 -m unittest discover -s tests -q

Failure tests reject changed original/source-review digests, invented photo
capabilities, a missing statistical-significance disclaimer, false
nationwide causal generalization, promotion of the management program
to a proven effective treatment, removal of missing links and asserted
unsupported intervention effects.

## Product conclusions and next gates

The second domain confirms that a well-scoped three-layer semantic map can
represent independently sourced local policy, scholarship and documented
tools while retaining consequential unresolved gaps.

**What remains to earn full product acceptance**:
- Obtain a genuine field-data or independently tested Program implementation
  for at least one problem; a documented product is not sufficient proof.
- Recruit unrelated researchers to perform the four tasks using the
  interface without guidance; record completion, misunderstandings and
  corrected design issues.
- Seek independent methodological review of cross-layer link status,
  including what is necessary before promoting a candidate relationship.
- Repeat with data refreshed at independently dated source snapshots,
  so study-specific uncertainty is never confused with real-world
  population change.
