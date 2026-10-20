# LLM-first, multi-source semantic investigation demonstration
**2026-10-20 · experimental · Cite-Refinery · stacked on draft PR #55**

This is a demonstration using **real primary-source material and model-authored reasoning** rather than TF-IDF/MiniLM relationship generation. It intentionally covers a substantive cross-field problem chain, not a topically similar cluster. The generator and skeptical critique were **both authored by GPT-6 in the same ChatGPT conversation**. Therefore the two passes are NOT independent model agreement, a blinded experiment or proof of autonomous ongoing investigation. The connected computer's Claude/Gemini CLI and local Ollama were previously unavailable, expired or too slow. We executed the real review and graph pipeline using model-generated JSON transferred directly to the authorized machine.

## Investigation question

**If a city wants to reduce dog-mediated rabies, what actually needs to be known, implemented and verified—beyond counting free-roaming dogs?**

The test covers five existing candidate graph modules:

- AW-01: free-roaming animal population observability;
- AW-02: population replenishment and reproductive control;
- AW-03: vaccination and One Health integration;
- AW-06: responsible ownership and free-roaming sources;
- PH-02: equitable healthcare access (PEP is specialist prophylactic care, not interchangeable with general primary-care provision).

## Genuine sourced material

All three public sources returned HTTP **200** on the authorized Linux host. Exact selected paragraphs and original HTML SHA-256 fingerprints are in `source_manifest.json` and `sources.json`. The full source must still be reviewed; we used bounded excerpts.

| Source | Evidence family **by origin**, not accepted graph layer | What it explicitly establishes |
| --- | --- | --- |
| [WHO rabies fact sheet](https://www.who.int/en/news-room/fact-sheets/detail/rabies) | WHO global public-health summary (Practical *lead*, not local measurement) | Dog exposure is the predominant global pathway; prevention includes vaccination of dogs, human PEP, health-worker training, surveillance and public awareness |
| [WOAH 2024 Terrestrial Code, Chapter 7.7](https://www.woah.org/fileadmin/Home/eng/Health_standards/tahc/2024/en_chapitre_aw_stray_dog.htm) | Program/policy guidance (not actual deployed program) | Dog population estimates inform planning; reducing dog turnover may help sustain population immunity; culling is not an adequate rabies-prevalence reduction measure; trend indicators may be preferable to repeated total counts for some program goals |
| [Belo et al. (2015), PLOS ONE, DOI 10.1371/journal.pone.0144830](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0144830) | Peer-reviewed academic methodological review | Raw counting of observed/photographed dogs without heterogeneous-detection correction does not automatically yield valid population abundance estimates |

No selected source supplies local vaccine coverage, bite-case rate, demographic turnover, PEP accessibility, or a causal impact evaluation. These three *types of evidence* are present in the corpus, but **all imported graph nodes remain neutral** until independently assessed.

## What GPT-6 actually reasoned

- **11 atomic propositions**, each pointing to an exact source substring, with scope, limitation, and module IDs. No quotation was fabricated; all 11 passed the literal/identity checks.
- **9 explicitly typed semantic connections** between propositions, all proposed as candidate or further unresolved, not automatically asserted as factual effects.
- **4 specific unresolved questions** to guide further data acquisition, including the vaccine-coverage denominator, vaccination turnover, patient PEP access and counterfactual impact evaluation.
- A second **same-model** skeptical critique tagged **9 propositions entailed / 2 partially supported**, and **8 relations plausible / 1 uncertain**. These are *model opinions*, not externally verified semantic accuracy.
- The uncertain `P8 → P1` link (WOAH's owned-dog/roaming statement qualifying Belo's specific detection-bias finding) is **not directly demonstrated by the selected paper**. It therefore becomes an `unresolved` edge with reviewer rationale instead of being treated as an established relationship.

The central insight is an **inference of required distinctions**, not a new validated field finding:

```text
Uncorrected sightings ──[possible bias]──> abundance estimate / coverage denominator
                                               │
                           program design and vaccine-dose monitoring
                                               │
                         births, deaths, roaming, movement and turnover
                                               │
                           sustained dog vaccination / herd immunity
                                               │
                    dog-to-human exposure and prevention strategy
                                               │
              separately observed human PEP reach and completion
```

Do not interpret this chain as a proven causal path or claim that specific local populations lack coverage. It is an investigation agenda derived from multiple authoritative texts.

**Important correction to a simplistic narrative:** WOAH explicitly distinguishes the pitfalls of mass dog culling from dog vaccination and humane management. The issue is not simply “fewer dogs = less rabies.” Similarly, a valid trend index can be appropriate for some management outcomes even if it is not a valid absolute population abundance estimate.

## A meaningful falsification control

We inserted a deliberately false **semantic inversion**: “WOAH establishes mass culling as effective at lowering rabies prevalence,” paired with a *real* WOAH excerpt saying mass culling is **ineffective**.

- The lexical citation check **passed the quote** because it exists.
- The GPT-6 semantic critique labeled the proposition **`contradicted`**.
- We saved the exact adversarial claim and critic output. This is a controlled, nonblind example of why quote-presence and vector similarity alone cannot provide semantic verification. It is not independent accuracy scoring.

## What successfully ran through the actual code

`cite-refinery-llm` consumed `gpt6_semantic_generation.json`, checked source IDs, exact quotations, scope and graph relation types, then consumed `gpt6_self_critique.json`, converted the reviewed output into `cite_refinery.semantic_graph.v1` and imported it in an **isolated new project**, with successful idempotent replay.

| Measured output | Result |
| --- | ---: |
| Real retrieved source pages | 3 |
| Investigated problem modules | 5 |
| Candidate atomic propositions | 11 |
| Semantic candidate bridges | 9 |
| Explicit open questions | 4 |
| Graph nodes | 23 |
| Graph edges | 40 |
| Candidate edges after critique | 39 |
| Unresolved edge after critique | 1 |
| Accepted empirical claims / effectiveness outcomes | **0** |
| Source quote check failures | 0 |
| Browser viewer | Chrome rendered 23 nodes and 40 edges, initialization true |

The included offline visualization `interactive_graph.html` loads the repository's **pinned Cytoscape.js** from `src/cite_refinery/vendor`, needs no internet connection and highlights unresolved relations with a distinctive dotted amber line. `graph_screenshot.png` is a real Chromium screenshot, not an AI-rendered mockup.

## Reproduce offline after cloning

```bash
D=research_materials/runtime_trials/llm_multisource_20261020
PYTHONPATH=src:. python3 -m cite_refinery.external_llm_cli \
  --sources "$D/sources.json" \
  --modules "$D/modules.json" \
  --response-json "$D/gpt6_semantic_generation.json" \
  --critic-response-json "$D/gpt6_self_critique.json" \
  --out /tmp/refinery-llm-demo

# Then inspect /tmp/refinery-llm-demo/candidate_packet.json.
# Open "$D/interactive_graph.html" in Chrome.
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_llm_multisource_demo_v1.py' -v
```

For fresh-source verification rather than the frozen offline corpus:

```bash
PYTHONPATH=src:. python3 scripts/demo_llm_multi_source_research.py
```

**Caution:** This refresh overwrites local fixture source files with content from the live pages, which may have changed since the frozen demonstration. Regenerated source excerpts may invalidate the pinned quote/fingerprint tests. Use in a disposable checkout when refreshing.

## Remaining capability gap

This demonstrates **model-authored semantics → quoted propositions → critique → graph revision**. It does **not** establish autonomous LLM orchestration, counter-source search, agent-initiated revisiting of missing nodes, model superiority over baselines, or verified causal conclusions. Those require a consistently reachable capable inference provider and proper independent blind evaluation. The existing research/landscape work remains unchanged.
