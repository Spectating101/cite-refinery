# Actual Atlas intelligence reality test — two genuine neural retrieval models

**2026-10-23 · Executed source-frozen development diagnostic, not an independent gold quality score.**

## Reproducible evidence

- Dedicated GitHub Actions run: https://github.com/Spectating101/cite-refinery/actions/runs/39950488908 — **SUCCESS**, including 13 contract/source integrity tests and two actual downloaded ONNX CPU pretrained model executions.
- Source: original frozen read-only standalone Atlas pilot: **1,497 cards**, Practical **57**, Academic **150**, Implementation **1,290**. Sealed **66** Academic holdout records never loaded; no approved real Nocturnal public investigations in this frozen corpus.
- Original source-card SHA-256: `1c116f51cdde33f3e80cb28b8c5fdf4c3a659dc43d9573a258f17f2a07d29668`, identical for both model runs. Actual model artifacts uploaded separately in the single workflow artifact `actual-1497-atlas-neural-retrieval-review-only`.
- Model and runtime: FastEmbed **0.9.0** on CPU, `BAAI/bge-small-en-v1.5` and `sentence-transformers/all-MiniLM-L6-v2`.
- The ten historical source targets and corresponding literal/paraphrase questions were **investigator-selected development probes**. They are **not blind** and do not provide full multi-relevant gold labels. **Do not call their hit rate semantic accuracy**, and don't optimize model choice solely to this exposed data.
- Source text embedded: title, summary and bounded public card metadata only — **not original papers, private Nocturnal records, untrusted repository code, model reference IDs or downstream question answers**. Nothing changed in the standalone browser itself.

## Measured retrieval, no simulated embeddings

| Selected target retrieved | Existing browser | BGE small | MiniLM |
|---|---:|---:|---:|
| Literal-query target, any rank (browser) | 10 / 10 | — | — |
| Literal-query target at top 1 | — | 6 / 10 | 5 / 10 |
| Literal-query target at top 5 | — | 9 / 10 | 10 / 10 |
| Paraphrase-query target, browser | 0 / 10 | — | — |
| Paraphrase-query target at top 1 | — | **5 / 10** | **5 / 10** |
| Paraphrase-query target at top 5 | — | **6 / 10** | **8 / 10** |
| Paraphrase-query target at top 10 | — | **7 / 10** | **8 / 10** |

**Paraphrase selected-target top-five by independent map:**

| Map | BGE small | MiniLM | Interpretation boundary |
|---|---:|---:|---|
| Practical (3 selected queries) | 3 / 3 | 3 / 3 | Navigation toward reported public observations; no actual approved real Nocturnal investigative case validated |
| Academic (4 selected queries) | 3 / 4 | 4 / 4 | Chosen abstract/title sources recovered; no verified measured result, study mechanism, causal interpretation or quote entailment |
| Implementation (3 selected queries) | **0 / 3** | **1 / 3** | Repository summaries grossly insufficient for detailed requested functionality and failure modes |

These small and source-chosen numbers support the statement that **neural metadata retrieval is an improvement over exact all-token lexical matching on these paraphrases**. They do not justify production semantic search or a general claim of accurate scientific reasoning. A pretrained embedding is *necessary but not sufficient* infrastructure.

## Implementation failure analysis: three real original repositories

The original selected-target rankings for the Implementation paraphrase probes:

| Investigator-chosen query | Repository reference | BGE rank | MiniLM rank | Source-informed fit caveat |
|---|---|---:|---:|---|
| “identify phantom wiring layer in comments on chip layout files” | `Mr-Fang-VLSI/EDAgent` | 876 | 152 | Original README describes broad EDA research automation and skill governance; does not verify this exact requested code-comment behavior |
| “classify patterns in host naming for externally visible systems” | `blisspixel/recon` | 241 | 2 | Original README describes passive externally visible domain technology/identity evidence, but not necessarily the precise classification asked |
| “protect sensor monitoring from invalid river gauge readings” | `WeixuanZ/flood-warning-system` | 95 | 20 | **Known adverse example**: source-pinned upstream NaN ranking fails; a separate lab adapter corrects bounded synthetic tests, so original code is *not* a verified solution to the protective requirement |

Source spot check: the original README blob identity for EDAgent `3d4cc492c79447509e656766133353a65129887e`; recon `093479bcc34ee586848204a05b1cb78bcccc85af`; flood-warning-system `fd2316be4fdf1ac210963268aba20c8a47e6000e` at the inspected upstream heads. Relevant frozen flood original-source repair test is independently documented and passing in Cite–Refinery PR #113; original source commit `c1c7facf2c5577a155edd93a0b7279ad7630518c`.

**Critical quality point:** Finding a repository associated with a topic is not the same as proving that its code satisfies the *action stated in the query*. The flood target is particularly misleading as a “correct solution” because its original implementation demonstrably fails the very NaN-safety example. Our archived reference is a navigation anchor, **not a functional suitability label**.

## Non-answerability exposure

Three separately declared prompts ask for independently established field/Nocturnal/scientific results absent from this pilot. Both embedding engines return nearest-neighbor source candidates anyway; **zero automatic safe abstentions** and **zero source-grounded natural-language semantic answers** were generated. No experimental field or paper-claim verification was conducted. A high cosine score cannot set the review flag to “accepted”.

The static original source map enforces useful constraints, but **the live answerability and entailment engine is not yet measured**. The existing 120 title-conditioned benchmark questions can be used as a development/reviewer queue, not evidence of an independent gold answer-quality test.

## Readiness assessment at this exact frozen checkpoint

| Component | Evidence observed | Decision |
|---|---|---|
| Source identity, corpus freeze, provenance, sealed holdout | CI passes for fixed 1,497/66 scopes, no original source leak | Operational development infrastructure |
| Practical navigation (public-safe metadata) | 3/3 selected paraphrases within top five in both models | Promising source navigation only |
| Independent Nocturnal investigative reasoning | No approved real snapshot attached | **Not demonstrated** |
| Academic navigation (abstracts and development metadata) | 3/4 BGE, 4/4 MiniLM top five | Promising, but sparse source text |
| Original-paper methods/results/limits interpretation | No original-paper entailment judged by this retrieval run | **Not demonstrated** |
| Implementation capability navigation | 0/3 BGE, 1/3 MiniLM top five | **Insufficient** |
| Implementation original code functionality | Separate narrow pinned source module tests exist | Some scoped engineering proof, no corpus-wide functional validity |
| Three-map source-to-source correlation and opportunity logic | No independently accepted relationships in frozen workspace | **Not demonstrated** |
| Answerability/abstention | Retrieval always produces candidate; zero safe abstentions generated | **Missing operational answer gate** |
| External competitive advantage | No independent competing tool/user study with full evidence labels | **Not demonstrated** |

## What to build next — minimal, source-depth first

**Do not select a “winning embedding model” from ten exposed development tasks and ship it.** Instead:

1. Design a small, independently adjudicated set of **30–60 authentic tasks**, stratified by map, including multi-relevant sources, no-answer requests, contradictory reports, source negations, temporal revisions and functionality-versus-topic discrimination. Don't write task titles into source fields or let judges see model outputs before labels are frozen.
2. Recover permitted **original paper passages and README/code snippets** with SHA-pinned sources, provenance and rights boundaries; never promote from external project descriptions alone. Run retrieval with depth and an independent claim-support check, including negative examples such as original flood NaN.
3. Reuse existing PaperQA2 retrieval and authorized live semantic model components rather than implementing another graph engine. Report quotation correctness, supported/unsupported claim rate and abstention separately from recall.
4. For Practical, complete a separate **Nocturnal-approved** case export and test timeline, identity resolution, correction/retraction, and source legality against authentic matters.
5. Only after standalone maps independently pass, test the cross-map bridge with **deliberately false but plausible joins** and opposing evidence, not merely one successful example. Compare to existing OSS and ordinary researcher workflows under equal evidence access.
6. Measure actual compute latency, cost, original-source checks and human analyst time savings. No current retrieval score establishes economic or institutional value.

**Result:** This pass establishes a real semantic *navigation layer* can improve on the literal browser and shows where it fails. It does **not** establish a fully autonomous intelligence system, functional suitability of the repository set, or product-market advantage.
