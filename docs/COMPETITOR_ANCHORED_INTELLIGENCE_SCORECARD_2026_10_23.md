# Competitor-anchored Atlas progress gate · 2026-10-23

**Status: competitor landscape verified, no intelligence-quality head-to-head has been executed.** This is the standing standard for evaluating future Cite–Refinery changes. The old 1,497-card pilot, ten paraphrase anchors, 21 hand-curated paper claims and the Science repository identity census are **internal development evidence**, not competitive product evaluations.

Source registry: `research_materials/competitive_reference/competitor_relative_progress_v1.json`. It records original links, evidence kinds, test obligations, reuse possibilities and unknowns for eight close substitutes. A recorded competitor feature is not automatically independent proof of that system's success on our workload.

## Current market-reality scorecard

| Job the user wants done | Strong current alternative | What the incumbent already does | Cite–Refinery tested evidence | Comparative position |
|---|---|---|---|---|
| **Find a scientific paper and provide a grounded answer** | [PaperQA2](https://github.com/Future-House/paper-qa) | Agentic PDF/text ingestion, evidence reranking, metadata/retraction checks, cited answers | Our PaperQA2 sparse retrieval indexed/retrieved 3 chunks; actual local answer inference timed out. MiniLM found 4/4 selected Academic paraphrases @5, but no source-entailment/answer quality proven | **Behind on demonstrated end-to-end QA; no controlled head-to-head** |
| **Synthesize multi-paper scientific findings** | [OpenScholar](https://www.nature.com/articles/s41586-025-10072-4) | Published retrieval/generation evaluation built on 45M OA papers and expert-written ScholarQABench tasks | Only 150 Academic browseable cards (103 development full-text source descriptions + 47 older abstract leads), 66 sealed holdouts; no blind multi-paper answer benchmark | **Behind on both scope and demonstrated synthesis; do not compare 150 to 45M as quality evidence** |
| **Conduct guided research extraction/systematic review** | [Elicit](https://support.elicit.com/en/articles/14757543-getting-started-with-elicit-which-workflow-should-i-use) | Research Agent discovery/extraction, guided screening and PRISMA reporting; Find Papers and Extract Data folded into Research Agent on **30 September 2026** | Standalone Cite/Atlas lacks a comparable source-backed complete systematic-review user workflow | **Feature parity not established** |
| **Cross-reference people and investigative records** | [OpenAleph](https://openaleph.org/docs/user-guide/103/cross-reference/) / [OCCRP Aleph Pro](https://aleph.occrp.org/) | Investigator documents, structured entities, cross-source matching, reviewer validation, large existing record sets | Frozen Practical map: 57 public entries mostly procurement; no Nocturnal-approved full public investigative snapshot. Native Nocturnal identity/review code exists separately | **Behind on integrated published investigation product proof; native Nocturnal value not dismissed** |
| **Find scientific software and its dependencies** | [ecosyste.ms Science](https://github.com/ecosyste-ms/science) | Scientific repository discovery and package/dependency links at much broader reported coverage | Exact-source 1,287-repo Science overlap: 398 matches / 889 nonmatches; 11/20 retrievable project contexts on fixed development sample | **Coverage complement, not a win; integrate metadata and keep original GitHub fallback** |
| **Compare research contributions across papers** | [ORKG](https://orkg.org/about) | Structured scientific problem comparisons and tabular contribution distinctions | ORKG read-only v2 paper-candidate access works, no verified finding or original scientific-claim comparison yet | **Unproven parity** |
| **Produce a cross-domain cited research dossier** | [ChatGPT Deep Research](https://help.openai.com/en/articles/10500283-deep-research-faq/) plus human analyst | Planning, multi-source synthesis, citations and structured research reports | No controlled end-to-end evidence-qualified problem → verified research → tested software → adoption obstacle dossier versus generic agent+human | **Differentiation unproven; this is the critical decision gate** |

**Scientific-review reality:** OpenScholar's peer-reviewed 2026 paper reports correctness advantages against GPT-4o and PaperQA2 on its own multi-paper evaluation; those numbers are **not** apples-to-apples with our ten selected retrieval targets. Our Oct 23 pinned original-study experiment found MiniLM NLI supported candidates **0/8**, DeBERTa **2/8** against investigator-authored labels; both largely abstained. No robust scientific claim verification is proven by those logits.

## What counts as progress, and what doesn't

**Not market-relevant proof alone:** source count growth, an internal PR merged, passing synthetic fixtures, a model returning some relevant link, verifying the SHA of a paper, retrieving a paper title, or a high similarity/confidence score. These are foundations, not substitutes for accepted answers or useful analyst workflows.

**Substantive progress relative to incumbents** must demonstrate at least one of:
- The same task with the same authorized source material is done with demonstrably fewer unsupported accepted claims, better original-code correctness, better documented contradiction/correction handling, or reliable abstention at comparable source coverage.
- A previously unhandled *specific* problem can now be resolved through an actual reproducible original-code trial and paper-source check with verifiable receipts, not simply a speculative cross-layer graph connection.
- Analyst time/cost is materially lower at equal or better human-reviewed output quality, with expenses and provider availability included.
- A mature substitute is integrated and the duplicated internal subsystem is actually removed or made optional, without losing evidence authority and privacy.

**No claim of 'better than X' is permitted without task-level side-by-side competitor outputs and independent answer review.**

## The test that would change the competitive verdict

Design and freeze **at least 30 authentic questions across three maps**, created independently of the code and without seeing candidate model outputs: 10 Practical (real legally cleared public cases, entity/retraction/timeline traps), 10 Academic (full original permitted passages, method/numerical/causal/negative/abstention), 10 Implementation (pinned reproducible source code, negative controls and deployment-fit constraints). At least one-third should be negative/unsupported/ambiguous where honest abstention matters. For cross-layer evaluation add a separate set of **false plausible joins** and true joins, adjudicated before evaluation.

Run each test against (a) the relevant incumbent (PaperQA2/OpenScholar, OpenAleph, Science/GitHub, or a general research agent), (b) Atlas-only existing implementation, (c) Atlas with justified OSS reuse, all with equal source access and disclosed environment/license limits. Where a service cannot be run, report **NOT_EVALUATED**, not a fabricated score or parity claim.

For every task collect: top-k source discovery, quoted source/citation correctness, numerical/causal support, source version and correction history, original functionality where relevant, unsupported confidently accepted claims, abstention precision and coverage, runtime/cost, and human analyst intervention. Preserve both the original output and blinded grader's rationale. An Atlas release claim needs usable end-to-end proof; a clean 10-target retrieval run cannot satisfy this gate.

## Decision rules applied to today's Atlas

- **Academic**: re-use PaperQA2 passage retrieval, ORKG metadata and a capable authenticated reasoning model with original quote offsets and tabular calculations; do not produce another citation search framework to compete with mature literature systems.
- **Practical**: Nocturnal remains the authoritative investigation/retraction system; use OpenAleph/FollowTheMoney conventions as integration inputs, not a replacement identity engine. Native sanitized case export remains a blocker.
- **Implementation**: keep the tested repository identity census, Science package/dependency context where available, and original-code replays; avoid calling a name-match a technological solution. The verified flood NaN failure is a good negative test, not a verified deployable warning system.
- **Cross-domain**: stop claiming novelty for graphs, embeddings, citation-aware answers or software inventories themselves; source-verified functional transfer is a potential differentiation requiring a controlled baseline.

**Overall assessment as of October 23, 2026: Ahead of the older lexical Atlas in internal semantic navigation; behind mature specialized alternatives on demonstration and breadth; independent end-to-end differentiation unproven.** The development focus should be closing these observed gaps, not increasing architecture size.

This document is a **review gate**. It does **not** imply a CI machine ran any third-party competitor model, established parity or completed independent user research. Update it when a new source-backed competitor feature changes the comparison, and after every meaningful capability benchmark—not after every trivial refactor.
