# Executed source-claim intelligence audit — MiniLM NLI fails to provide useful source judgment

**2026-10-23 | source-derived scientific development cases, not independent label gold.**

## Authentic run and frozen inputs

- Actual executable NLI workflow: https://github.com/Spectating101/cite-refinery/actions/runs/39954061613 **PASSED** (8/8 targeted source/safety tests and genuine PyTorch CPU inference).
- Model: `cross-encoder/nli-MiniLM2-L6-H768`, pinned original HF revision `f3b1e8aac2451320dfe2ce56673b3f2ec63e6f03`; `sentence-transformers==5.1.2`. Model responses were real three-class logits, not developer-supplied JSON.
- Original casebook: `research_materials/runtime_trials/fulltext_dog_20261020/benchmark_cases.json`, DOI `10.14202/vetworld.2026.2816-2849`, 21 investigator-curated source-derived cases (eight entailed, eight contradicted, three overreach, two unresolved). Four synthetic *source swaps* were appended **before** inference. No labels/reasons were in model input.
- Fixed review policy: `max_softmax >= 0.90`, runner-up margin `>= 0.20`, `neutral` always abstains. The gate produces only **review candidates**, never scientific approval.

## Real inference results

| Gate outcome | Count |
|---|---:|
| Source-derived claims + mismatched-evidence controls | 25 |
| Abstained as requiring original-source review | **24 / 25** |
| Candidate *supported* after threshold | **0 / 25** |
| Candidate *contradicted* after threshold | **1 / 25** |
| Candidate contradiction that matches curated label | **1 / 1** |
| False candidate supports | **0**, because **no candidate supports were generated** |
| Overreach source cases safely abstained | **3 / 3** |
| Unresolved source cases abstained | **2 / 2** |
| Precommitted mismatched-evidence controls abstained | **4 / 4** |

**The low false-positive count is not an accuracy success. This gate rejected essentially everything, including all eight genuinely supported cases.** A system that always abstains is safe from unsupported acceptance *by definition*, but supplies no useful independent answer capability.

## Raw three-way maximum-label diagnostic (before threshold; NOT 4-class accuracy)

| Curated reference group | Cross-encoder top-score labels |
|---|---|
| Eight 'entailed' | 3 entailment; **5 neutral** |
| Eight 'contradicted' | 2 contradiction; **6 neutral** |
| Three 'overreach' | 2 neutral, 1 contradiction (model has no 'overreach' class) |
| Two 'unresolved' | 2 neutral (not equivalent to verified correct unresolved scientific status) |
| Four unrelated-evidence swaps | 4 neutral |

Source examples exposing the failure:
- **B01**: original study count endpoints explicitly paired with a precise scoped claim: NLI top entailment probability **0.797**, below fixed review threshold. It is not confidently accepted.
- **B03**: table p-value `0.55488235`, claim that decline is statistically significant: NLI top class **neutral, 0.964**. It fails to explicitly flag the false numerical significance conclusion.
- **B06**: specific p-value `0.038` stated as a claim: NLI top class **neutral, 0.881**. Scientific table parsing is weak.
- **B11**: study admits unable to conduct systematic surveys, whereas the claim says surveys were conducted: contradiction only **0.492**, thus gate abstains.
- **B13**: study explicitly says rabies impact could not be accurately quantified while claim says it was precisely quantified: contradiction **0.978**, the sole clear candidate contradiction.
- **B20/B21**: data-inaccessible hypothetical and unverified external replication cases: neutral high confidence; safe review abstention occurs but does not prove nuanced independent understanding.

## Key implementation decision

**Do not ship or merge this as a production semantic claim-support oracle.** Reusing a lightweight general NLI cross-encoder is possible as a supplementary candidate-review signal, but its inability to reason over original scientific tables, study designs, conditional statistical calculations, causal qualifications and multiple estimands makes it unsuitable as the primary claim judge.

The next *substantive* intelligence gate should reuse the existing source-bound semantic-answer path with a capable authenticated reasoning model, original permitted source text verified by SHA and contiguous quote offsets, and explicit contradiction/numeric checks. Run the 21 archived development cases plus **separate independent/new questions**, ask for exact source passage and rationale, and measure rejection of false effects and truly unanswerable queries. Multiple judges and unbiased holdout labels will be necessary for external capability or market superiority claims.

**The prior archived 18/21 result was from a different LLM and evaluator prompt. It is not comparable as a controlled head-to-head to this three-class NLI triage test.** A 3-way NLI classifier cannot itself produce the four-way source-interpretation labels expected of a scientific methods reviewer.

No original article full text was independently re-downloaded/re-hashed in this run; some evidence records are curated study summaries rather than byte-verified original passages. The 66 sealed Academic holdouts and Nocturnal private material remain untouched. Both actual model and prompts were used only for review outputs; **zero graph/scientific promotions**. The broader GitHub repository test workflow is red on preexisting optional runtime conditions and is distinct from this scoped NLI job.
