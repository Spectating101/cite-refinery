# Actual original-source claim triage — independent neural NLI gate v1

**2026-10-23 · Draft source-claim *development* experiment, with model inference and provenance separated.**

## Why this instead of another embedding or graph engine

The last test showed **MiniLM 8/10** developer-selected paraphrase target hits at top five on 1,497 frozen source cards, but did not evaluate scientific claim truth, missing evidence or abstention. We already own a difficult, source-derived 21-case Anuradhapura scientific study set. This PR asks whether a genuine pretrained three-way NLI model can **flag candidate supported, contradicted and unresolved claims** from actual excerpts without promoting weak evidence as science.

Original dataset: `research_materials/runtime_trials/fulltext_dog_20261020/benchmark_cases.json`, linked to DOI `10.14202/vetworld.2026.2816-2849`, author-curated 21 comparisons (8 entailed, 8 contradicted, 3 overreach, 2 unresolved). The archived prior LLM diagnostic reported **18/21** matches to investigator labels, but **0/2 unresolved cases correctly labeled**. This is a *model-development diagnostic* against researcher-selected examples, not a blind independent scientific study.

Some source fields are quoted article fragments while others are investigator-constructed numerical/context summaries. Their original fulltext SHA receipt is archived, but this CI does **not** independently fetch or verify the full published text or recompute the original excerpt offsets. Therefore this is **frozen source-derived excerpt judgment**, not fully source-verified original article interpretation.

## Actual third-party model reuse

- `cross-encoder/nli-MiniLM2-L6-H768`, pinned to Hugging Face model revision `f3b1e8aac2451320dfe2ce56673b3f2ec63e6f03`, executed with CPU `sentence-transformers==5.1.2`. Three genuine labels: contradiction / entailment / neutral. Source pairs are `(evidence excerpt, specific claim)` and model sees **no reference labels, assessor rationales, future test scores or repository IDs**.
- Confidence gate is precommitted to **at least 0.90** top softmax and **at least 0.20** separation from the runner-up, with **neutral always abstaining**. These are *not calibrated safety thresholds*: low confidence, disagreement or neutral produces `abstain_needs_original_source_review`.
- High-confidence NLI results are `candidate_supported_requires_original_source_review` or `candidate_contradicted_requires_original_source_review`. **Neither is automatically accepted**, regardless of score. Scientific extrapolation, method validity, multiple testing, provenance of measurements and contradictory reports still require source checks and human adjudication.
- Four original-source **cross-swapped negative controls** are precommitted (B01 versus B09 passage, B06 vs B01, B12 vs B08, B19 vs B10). This is not a real-world sampling distribution. It reveals cases where the model incorrectly claims textual support for a claim using clearly unrelated source evidence.
- The code refuses non-finite logits, unexpected three-way model label mappings, unknown/falsified source casebook counts, incomplete inputs, and overwriting earlier reports. It records each case's confidence, source excerpt SHA-256, claim SHA-256 and whether model would propose a source-claim review.
- `tests/test_actual_claim_entailment_gate_v1.py` uses **test-only synthetic logits** for safety contracts. These are never reported as actual NLI accuracy. The CI job must separately install the pretrained model, fetch the pinned public weights and run inference or fail explicitly.

## Measurements

The dedicated GitHub Actions workflow `.github/workflows/actual-source-claim-nli.yml` prints original-gold-class breakdowns of actual triage output, including all false candidate supports, candidate contradictions against other labels, coverage of the two unresolved cases, overreach and four intentionally swapped sources.

The report preserves original annotated status and *model signal* separately. Candidate interpretation still needs independently verified source text and a reviewer to become scientific evidence. Do not mistake this for a new sealed Academic holdout evaluation: the original 66 heldout papers are never loaded, and the 21 curated claims are an older development set. No Nocturnal public release or original-code execution is performed by this NLI classifier.

## Acceptance conditions and stopping rule

- If a source-mismatch negative is marked confidently supported, the model cannot be a standalone entailment acceptance gate.
- If overreach or unresolved questions are marked confidently supported, do not auto-promote (the current program already forbids it).
- Even if all chosen cases match, there is **no** independent accuracy or safe-autonomy claim. Human-adjudicated, authentic domain-mixed and adversarial source material must follow.
- If general NLI is weak on numerical or estimand distinctions, **reuse an inference model but require dedicated numerical/table logic and original-source passage checks**. No more custom inference framework merely to rescue a poor score.
- We should treat practical Nocturnal investigation records and technical implementation code-function evidence through their dedicated source-authority checks, not assume this Academic NLI is a universal cross-map judge.

**No results are declared before executed GitHub Actions evaluation is inspected.**
