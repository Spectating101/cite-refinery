# Bulk source dump and emergent semantic atlas — pilot v1

**20 October 2026.** Cite-Refinery now has a breadth-first corpus collection and AI mapping workflow that does not supply the mapper with predefined problem modules.

## Real corpus acquired

63 distinct public source records were retrieved in one frozen local collection:

- 16 Europe PMC scholarly abstract records.
- 31 OpenAlex reconstructed scholarly abstract records.
- 16 direct institutional webpage excerpts.

The collector used eight broad topic coverage quotas: dog management, extreme heat, electronic waste, food redistribution, flooding, battery recycling, indoor air, and digital platform employment. **These collection topics are a source-selection bias**; their labels and predefined practical/academic/program ontology were not passed to the mapper. The model saw stable-hash-shuffled source passages in seven batches. Retrieval had zero reported errors; retrieved material is still mainly abstracts and partial institutional pages, not complete scientific corpora.

The actual full extracted publisher material is retained privately on authorized Optiplex:

    /home/phyrexian/ResearchDumps/cite-refinery/open_corpus_20261020/

Archive:

    open_source_dump_and_map.tar.gz

It contains complete private_corpus.json, full mapped records, global_atlas.json, source_manifest.json and blinded_review_queue.json. Directory and files use restricted permissions. The raw publisher passages are NOT committed to GitHub. Public repository artifacts contain the source URLs, passage SHA-256 digests and model-paraphrased provisional readings.

## Actual semantic mapping results

Gemini 3.8 Flash Medium through authenticated Antigravity performed seven source-grounded mapping calls and one global consolidation.

| Outcome | Count |
|---|---:|
| Input distinct source records | 63 |
| Verified quoted-source candidate readings | 63 |
| Batch-local emergent groups | 30 |
| Batch-local proposed source relations | 27 |
| Batch-local research unknowns | 29 |
| Synthesized global problem areas | 8 |
| Global cross-area analogies | 3 |
| Sources intentionally left unplaced | 6 |

The eight provisional areas are:

1. Free-roaming dog demography, vaccination and rabies protection — 6 sources.
2. Lithium-ion battery material recovery and scaling — 6.
3. Informal electronics and lead-acid waste occupational toxicants — 9.
4. Heat mortality projections and warning implementation — 7.
5. Urban floods, early warnings and health risk — 7.
6. Indoor/classroom air quality and pediatric respiratory health — 8.
7. Algorithmic management and platform worker injuries — 6.
8. Food surplus redistribution, logistics and nutritional gaps — 8.

Some sources may appear in two related areas. Six institutional excerpts were left unplaced. The three limited cross-area links concern (1) heat/flood warning implementation, (2) battery/e-waste worksite hazards, and (3) platform/food-rescue logistics. All are *hypotheses for comparing studies*, not established causal relations.

Every first-pass source quote was checked as an actual substring in the source's locally retrieved passage. This **does not independently establish semantic entailment or scientific truth**. The global consolidation may add overreaching interpretations; independent review is needed before making factual or causal commitments.

## Outcome and corpus leakage safeguards

Three sources were initially assigned a candidate measured-program-outcome label. They include:

- The previously studied Anuradhapura dog population program, which must NOT be treated as a new independent holdout; its program metrics do not establish human rabies reduction.
- A small Ukraine dog vaccination/serology sample, which does not establish durable community-wide immunity.
- An article-reported IoT food surplus pilot with quantity rescued and pickup-time claims, which does not establish recipient nutrition improvement or independent commercial validation.

Other WHO-hosted materials include program guidance and launches; institutional hosting is not proof of implementation or demonstrated effects.

## Structured Cite-Refinery graph

The map was staged in a separate, neutral review project:

- 79 neutral nodes: 63 source readings + 8 mapped areas + 8 evidence-gap questions.
- 68 candidate/unresolved edges.
- Graph packet receipt sgpacket:203a1115253ec6af.
- The same packet was imported a second time and confirmed idempotent.
- Zero accepted scientific claims, interventions or verified cross-domain causal effects.

## Blank independent review packet

Twelve source passages from the three retrieval families were separately selected for a human-blinded evaluation. AI labels, mapping areas and verdicts are excluded from the review packet. **No independent labels exist yet**; no accuracy scores or reviewer agreement were manufactured. Only its source-ID/status manifest is shared through GitHub.

## Reproduction

Using cite-refinery-corpus-map:

    cite-refinery-corpus-map --corpus-dir /tmp/my-corpus --map-dir /tmp/my-map collect
    cite-refinery-corpus-map --corpus-dir /tmp/my-corpus --map-dir /tmp/my-map status
    cite-refinery-corpus-map --corpus-dir /tmp/my-corpus --map-dir /tmp/my-map map-shard --index 0 --provider antigravity --model gemini-3.8-flash-medium
    cite-refinery-corpus-map --corpus-dir /tmp/my-corpus --map-dir /tmp/my-map assemble
    cite-refinery-corpus-map --corpus-dir /tmp/my-corpus --map-dir /tmp/my-map synthesize --provider antigravity --model gemini-3.8-flash-medium

Map every available shard before assemble. The collector's broad search queries are configurable in Python. Copilot remains the default provider unless explicitly overridden. Nothing auto-cycles Copilot accounts, merges, deploys, or imports third-party files beyond the documented public source interfaces.

## Assessment and next gate

This is a **working corpus-to-candidate-map** prototype, and notably more independent of hard-coded problem modules than the previous single-topic dog pipeline. It is not a fully independent benchmark or a comprehensive mapping of the world: the eight collection quotas selected the source universe, abstracts are incomplete primary evidence, some materials repeat prior research, and Gemini role readings are unverified.

Next: expand the bulk corpus to include genuine field case reports, municipal/program implementation records, original datasets, and methods papers; independently adjudicate new unseen sources and links; score false program-outcome attribution, missing-node recall, and semantic precision.
