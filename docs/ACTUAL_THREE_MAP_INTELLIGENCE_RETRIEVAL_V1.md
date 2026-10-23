# Atlas intelligence gate — actual pretrained semantic retrieval, not an end-to-end reasoning claim

**2026-10-23 · Standalone evidence-limited map experiment on the frozen corpus.**

## The question we can actually test today

The frozen source-only browser has 1,497 records: Practical **57**, Academic **150** and Implementation **1,290**, with 66 Academic holdouts sealed and no Nocturnal approved-real case release attached.

The pre-existing development diagnostic used 10 **investigator-chosen** source targets and two queries per target. With the actual browser's all-token substring retrieval, 10/10 literal queries found their target, but 0/10 meaning-preserving paraphrases found the corresponding card. This establishes an obvious *development* limitation in lexical navigation, not a population-level estimate of retrieval quality.

This branch performs the next experiment, not another simulated AI receipt: it actually loads an open pretrained **BAAI/bge-small-en-v1.5** model through **FastEmbed 0.9.0** (ONNX, CPU) and embeds the exact same 1,497 existing source cards and the 20 literal/paraphrase queries. It records real per-layer target rank, top-1/top-5/top-10 retrieval, cosine scores and the unchanged browser baseline. The model is not fitted on test answers. Metadata indexing omits source IDs and URLs, only including bounded card titles, summaries, subjects, tags and short existing details.

Three extra **predeclared unsupported-result prompts** explicitly ask about source validation that the frozen workspace lacks. The retriever is expected to return some nearest-neighbor text, which does **not** give it authority to answer or to invent a deployment, scientific replication, or completed Nocturnal case. Those prompts **are not semantic retrieval ground truth**; they reveal the structural need for an answerability/abstention gate.

## What this does *not* measure

- The ten semantic paraphrase targets were selected by investigators with foreknowledge of corpus items; there are no independently annotated relevance sets, out-of-time blind evaluation, or statistical generalization across 1,497 records.
- Some meaning-preserving user requests can have multiple legitimate sources; the target is one development anchor, not the only relevant document.
- **No actual paper bodies, source statements, experiment executions, field outcomes or Nocturnal private investigation files are loaded into the embedding index.**
- Embedding similarity does not entail evidence support, technical feasibility, causality or market conversion. No model-generated answer, verified quoted passage, safe abstention engine, cross-layer causal relation or independent investigator performance is measured by this test.
- Model name and FastEmbed version are recorded, but the downloaded weight artifact SHA/revision is not independently pinned, so cross-date floating-point scores may change.
- No neural model is connected to the existing standalone web UI by this PR, and the 120 prepared title-conditioned source questions are not falsely reported as blind semantic gold.
- Even a 10/10 neural top-1 result (should it occur) would be a **small curated development benchmark**, not a claim of an intelligent end-to-end product.

## Evidence and safety contract

The existing `three_map_capability_packet._check_pilot` enforces original 1,497 counts, exact unique source identities, absence of original bodies or holdout in card payload, and existing source qualification limitations.

The new test suite detects invalid dimensions, nonfinite vectors, degenerate embeddings, altered layer scope, holdout leaks, and claims of scientific/functional/cross-layer promotion. Its injected test-only numeric vectors **are not used in the real CI measurement**. The real CI installs the actual FastEmbed model separately, runs it on the full source cards, emits exact per-map ranks, and fails visibly if model acquisition or encoding is unavailable. **No silent TF-IDF fallback** or fabricated semantic result is permitted.

### Run on your own authorized machine

```sh
python -m pip install -e . 'fastembed==0.9.0'
python -m unittest discover -s tests -p test_actual_semantic_retrieval_replay_v1.py -v
python -m cite_refinery.actual_semantic_retrieval_replay \
  --pilot /path/to/actual/original/standalone/atlas.json \
  --out /tmp/atlas-actual-semantic-retrieval.json
```

The GitHub Actions workflow `.github/workflows/actual-three-map-semantic-retrieval.yml` constructs the original offline 1,497-card pilot from source manifests, records all 23 source-aware probes and uploads one **review-only** JSON artifact.

## Next independent evaluation after this experiment

1. Replace title/author-hint questions with independently authored user questions; adjudicate entire relevance sets, unanswerable tasks and risk-sensitive cases using original permitted source passages.
2. Evaluate retrieval **and** original quotation/scope entailment jointly, not just rank. Require separate source authority and temporal resolution.
3. Verify independent standalone Nocturnal reasoning with **publication-approved** materials and actual timeline/corrections. Existing 57 Practical metadata entries are not these cases.
4. Verify 103 Academic source findings with actual original sources and independent evaluation, preserving 66 sealed holdouts for authorized operators.
5. Verify original-code functional results on multiple true source-pinned Implementation projects, including failure paths and licensable adoption requirements.
6. Compare Atlas versus a domain-appropriate existing OSS + model workflow under equal constraints and blinded human evaluation; record latency/compute costs and false accepted claims.
7. Advance promotion/release only when source quotation, semantic answer accuracy, calibrated abstentions, original code behavior and grounded cross-layer link quality are independently verified.

**Current starting verdict: SOURCE_NAVIGATION_WORKS_BUT_LIVE_SEMANTIC_INTEGRATION_NOT_DEMONSTRATED.** The model trial may revise semantic retrieval evidence after its CI executes; it does not automatically revise end-to-end Atlas capability.
