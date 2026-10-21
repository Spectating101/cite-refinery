# Standalone Academic Atlas — research depth, not bibliography breadth

**Scope:** make Cite–Refinery's Academic map useful independently of Nocturnal, software assets, opportunity ranking and commercial conversion.

## Existing material reused

The Oct 20 frozen public **development-only** manifest includes exactly 103 original-source identities: **43** Europe PMC open-access full-text records, **31** World Bank report text records and **29** Zenodo dataset metadata records. A separate **66-record holdout stays sealed**. Only 101 of 103 development records met the earlier minimum text length for LLM mapping; this atlas does not mislabel all 103 as semantically mapped.

These records are independently **indexed**, not automatically scientific truths. In particular a PMC document is not necessarily an original empirical study; a conference proceeding can be indexed, without being counted as a validated experiment.

## Data authority

- Original source IDs, HTTPS canonical URLs, publication metadata, source type and extracted-text SHA-256 remain unchanged.
- A full-text index means source text was previously retrieved by the development-corpus acquisition process, **not** that we currently have its content inside this Git repository, have checked results, or have verified peer review.
- World Bank text is a published institutional report, **not independent program outcome measurement**.
- Zenodo record is catalog metadata/file inventory. No dataset row, figure or scientific finding is inferred.
- The entire source text and held-out data stay in their restricted source locations. No original article text is copied into the generated map or CI artifact.
- This module has no new crawler, network access or console entrypoint. It attaches to the existing `cite-refinery investigate map-foundations` workflow.
- It does not sum the original 47 abstract-index records with the newer 43 article records as though source overlap were independently ruled out.

## What can actually be inspected

1. **Research inventory:** individually navigable article, report and dataset catalog identities; source scope, date, type, extracted words, text fingerprint.
2. **Claim-level evidence receipts:** analyst-supplied `method`, `result`, `limitation`, `contrary_result` and `research_question` records must cite an exact character span in a locally held original extracted source matching the frozen SHA-256. Each claim carries population, setting, outcome and study-design scope.
3. **Contrary-evidence *questions*:** optional pairwise comparison references two separate previously anchored publications. These are explicitly **candidate scope tensions**; no false adjudicated contradiction from overlapping vocabulary.
4. **Balanced review worklist:** stable-hash sampling among still-unreviewed source types, not a supposed best-field score. Dataset review asks about underlying data availability, never converts metadata into study claims.
5. **Independent within-layer search:** literal title, original URL, source class and scoped analyst interpretation. No false semantic-embedding or scientific accuracy claim.

Even an exact text-anchored claim means only that the original extracted document **contains those words**. The author's findings, methods, generality, causal effects and reviewer's interpretation remain distinct and contestable.

## Canonical command

```bash
cite-refinery investigate map-foundations \
  --academic-development-manifest research_materials/runtime_trials/richer_corpus_20261020/development_source_manifest.json \
  --academic-split-receipt research_materials/runtime_trials/richer_corpus_20261020/frozen_split_receipt.json \
  --academic-genre full_text_jats \
  --academic-atlas-out /tmp/academic.json \
  --academic-review-backlog-out /tmp/academic_backlog.json \
  --json-out /tmp/layers.json \
  --markdown-out /tmp/layers.md
```

The Academic map is embedded in `layers.academic.development_evidence_atlas` and can be emitted independently through `--academic-atlas-out`. The existing 47 source abstract leads and external DOI identity audit remain separate.

### Optional source-anchored review packet

The workflow accepts `--academic-evidence-reviews /private/review.json` with schema `cite_refinery.academic_evidence_reviews.v1`, along with `--academic-review-text-dir /private/academic-texts` containing files named `<source_id>.txt`. Each text must be the original extraction whose SHA-256 is in the frozen manifest. No arbitrary paths in the JSON review packet are opened.

Review packet example (fictional only):

```json
{
  "schema": "cite_refinery.academic_evidence_reviews.v1",
  "claims": [
    {
      "id": "claim-a",
      "source_id": "PMC-demo-a",
      "start": 7,
      "end": 63,
      "quote": "Researchers recorded methods across fictional clinics.",
      "statement": "The authors describe their sampling procedure.",
      "role": "method",
      "review_state": "candidate",
      "scope": {
        "population": "fictional participants",
        "setting": "fictional clinics",
        "outcome": "data recording",
        "study_design": "not yet independently adjudicated"
      }
    }
  ],
  "tensions": []
}
```

Offsets and source hashes are validated; this example is illustrative and must be recalculated against its exact fictional source body before use. The emitted atlas retains the **quote SHA-256 and offsets**, not the original quoted passage. Reviewer-designated `analyst_source_span_checked` additionally requires an operator/reviewer identifier and date; it **does not** elevate the claim to scientifically valid.

## Acceptance gate

The automated test suite uses the repository's **actual frozen 103-record development manifest and public 66-record holdout seal**. Negative fixtures test altered content hashes, invented quotation spans, duplicate source identities, illegal dataset-to-finding promotion, forged authoritative roles, and source comparisons masquerading as independent contradictions.

Current substantive limits:

- **0 independently validated scientific findings** produced by this source index.
- **0 verified conflicting scientific effects**; comparison questions are review queues only.
- **0 original full-text claims independently reviewed by this PR** until review packets backed by the real frozen source texts are supplied.
- No blind held-out human annotations or model generalization scores.
- No population-wide or all-fields coverage percentage, semantic model scoring, forced vertical ranking, asset arbitrage or cross-map join.

**Next evidence move:** bring the original 43 accessible development article texts into the analyst review environment, run a balanced methods/results/limitations review, evaluate scope and disagreement independently, and only then compare against the sealed holdout under a separate blind evaluation protocol.
