# Three standalone maps — frozen-corpus capability gate v1

**2026-10-22 | draft evaluation infrastructure, not a model result, integration verdict, or release.**

## Why this track exists

The market comparison found that competing products already have extensive source discovery and graph linking. The Atlas must show *evidence interpretation, defensible abstention, and qualified original implementations*, not merely a larger source index.

The October 22 pilot is exactly **1,497 public-safe browse cards**: Practical **57** (nine unverified reports and 48 procurement notices), Academic **150** (103 development identities and 47 separately classified older abstract leads), Implementation **1,290** (1,287 surveyed repositories and three off-survey historical test identities). Sealed Academic holdout: **66 records**, neither loaded nor used here. The pilot **does not contain approved real Nocturnal investigations**.

## Deliverable, reproducible on existing frozen source receipts

`src/cite_refinery/three_map_capability_packet.py` generates a **predeclared, deterministic, source-balanced sample** from the original offline pilot:

| Layer | Distinct original source cards | Distinct challenge questions | Primary gap tested |
|---|---:|---:|---|
| Practical | 20 | 40 | Reconstruct claims/timelines, separate reported allegations and public records, abstain on unproven outcomes |
| Academic | 20 | 40 | Distinguish quoted results, methods, limits, population and causal overreach |
| Implementation | 20 | 40 | Demand exact pinned-code functional replays, negative tests, field/reuse caveats |
| **Total** | **60** | **120** | Development-review queue; **zero independent answer-quality labels** |

Source groups are proportionally allocated with at least one per genre. Implementation records are additionally stratified by **reported evidence stage** (tested source function, source-inspected, commit-checked, metadata-only, historical/off-survey), where such stages exist, to avoid 20 near-identical untested GitHub leads. These are publisher/receipts stages, not validated capabilities. Within each stratum the original record IDs are deterministically SHA-selected from a declared seed. The sampler rejects any changed baseline totals, leaks of source bodies/holdouts, altered original evidence authority, and missing known development anchors. It fingerprints the full source-card metadata, not just record counts.

The second output is a reviewer reference containing anchors to the selected source cards; these are *sampling anchors*, not independent retrieval relevance judgments or proof that the candidate source entails any answer. Do **not** expose it to the model under test. Question-only delivery and review material should be stored in separate workspaces for a genuine blind trial.

The generator also reproduces the earlier **ten historical investigator-chosen** direct/paraphrase probes against the actual browser's literal search rules. Expected old baseline: **10/10 direct, 0/10 paraphrase targets**, a development diagnostic only, never scientific correctness.

## Run from existing CI Atlas artifact

```bash
python -m cite_refinery.three_map_capability_packet \
  --pilot /path/to/standalone-research-pilot/atlas.json \
  --out-dir /tmp/cr-independent-capability-packet

# Outputs:
# questions.json           (question-only task list; no selected record IDs)
# reviewer-reference.json  (sampling source anchors, genre counts, historical smoke probes)
```

The map-foundations CI now performs focused tests, constructs the packet using the same actual frozen pilot it generates, checks 60/120 counts and historical smoke signatures, and uploads artifacts **only if GitHub Actions executes and passes**. CI success proves deterministic packet integrity, not model performance.

## Comparing different agents or competitors

Use the *same* question-only packet with a fixed source-access policy, fixed time/token budget, declared model/tool configuration and result retention. A system result can be supplied as:

```json
{
  "schema": "cite_refinery.three_map_capability_predictions.v1",
  "baseline_sha256": "<copy from questions.json>",
  "responses": [
    {
      "task_id": "PRA-01-1",
      "retrieved_card_ids": ["practical:reported_case:<exact-original-id>"],
      "abstained": false
    }
  ]
}
```

Then run the same generator with `--responses /path/to/predictions.json` and a *fresh* `--out-dir`. It will write `diagnostic-results.json`, which reports submission coverage, abstentions and inclusion of the developer-selected source anchor per map. Predictions with the wrong corpus fingerprint, duplicated tasks, duplicate source IDs, or source IDs outside the frozen map are rejected. **This is not a semantic accuracy, precision, or competitive-win score**. A selected source match might be coincidental or unhelpful. **Source-bound questions contain part of the record title**, so an anchor hit is deliberately an easy *navigation check*, not a semantic retrieval challenge. Use the historical paraphrase probes (and independently written new queries without target-title leakage) for genuine meaning-level retrieval evaluation.

For genuine performance, **before seeing predictions** independently adjudicate relevance sets, exact source/passage evidence, answerability and substantive entailment; capture disagreements between reviewers and a frozen judge receipt. Only then compute recall@k, precision@k, support/contradiction error rate, safe abstention, explanation quality and elapsed time. Quotes and SHA checks verify source identity, not the scientific entailment of a conclusion.

## Deferred / delegated execution

1. **Practical:** the private Nocturnal → Practical cross-repo contract (#111) must run and pass. Then evaluate legally approved original investigation outputs; do not silently add private material to this frozen public packet.
2. **Academic:** recover exact original permitted source bodies by SHA and run authorized live inference independently; the Optiplex semantic handoff is separate, and the 66 frozen holdout identities remain sealed.
3. **Implementation:** increase source-pinned original functional tests from the known two modules, recording failures and rights restrictions. No test of a mock or synthetic fixture alone establishes field deployment.
4. **Opportunity discovery:** only after independent judgments are strong, produce five full problem → science → functioning implementation dossiers, including rejected candidates and commercial/adoption blockers.
5. **External competition:** compare complete investigator workflows against specialist tools, not one feature at a time. A funding or price hypothesis is not a validated revenue claim.

## Stop/go rules

- **KEEP / SCALE** only where independently annotated performance rises without unsupported evidence promotion, and source-specific capability tests are reproducible.
- **REPAIR** unreliable retrieval, grounding, source integrity or execution before increasing corpus size.
- **NARROW** a map if the standalone usefulness or obtainable original rights remain too poor for defensible conclusions.
- No arbitrary target thresholds are declared as measurements. Any target must be precommitted ahead of a genuinely independent evaluation.

The frozen branch `freeze/cite-refinery-semantic-optiplex-handoff-2026-10-22` and the sealed holdout remain untouched. This work is stacked on Cite–Refinery #109 and does **not** merge into main.
