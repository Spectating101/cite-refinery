# Controlled publisher-source authentication in the unified investigator

October 21, 2026. Draft continuation of generic intake PR #88.

## Engineering decision

Do **not** allow arbitrary HTTP retrieval for user-supplied references. The existing `cite-refinery investigate` controller now has an explicit `verify-evidence` command using narrow read-only adapters for public GitHub issues, **exact 40-character-commit-pinned** GitHub source files, and Europe PMC MED/PMID abstracts.

This adds one reusable source-authentication utility to the *existing* investigator, not another standalone CLI, research campaign engine, or conceptual layer. The foundational graph remains **Practical ↔ Academic ↔ Implementation**. Economics/value is downstream.

## Workflow

First initialize as in PR #88 using a local `cite_refinery.supplied_evidence.v1` JSON file with 1–6 records in the three source families. The supplied URL is not automatically visited, and the supplied text is not yet authenticated.

Then explicitly request publisher verification:

```sh
cite-refinery investigate --workspace /tmp/my-investigation \
  verify-evidence --id SESSION_ID

cite-refinery investigate --workspace /tmp/my-investigation \
  status --id SESSION_ID
```

A successful result records `publisher_passage_matched_claim_unreviewed` only when the supplied passage appears as a case-sensitive contiguous sequence in the fetched original record, allowing whitespace and HTML entity normalization. No LLM judgment is involved in this test. The persisted session records the submitted text SHA-256, publisher content SHA-256, publisher URL, record type, timestamp, and a verified Git blob SHA-1 for source files.

A missing substring produces `submitted_text_does_not_match_publisher`; unsupported URL routes or a family/provider mismatch abstain without fetching. A network failure becomes `publisher_verification_unavailable`, **not a fraudulent-text assertion**. A GitHub issue endpoint returning a pull request, a mismatched issue ID, a Git blob digest mismatch, a missing Europe PMC PMID or an altered local text hash fails closed.

The current provider routing is deliberately conservative:

| Declared layer | Permitted source route | What is *actually* established |
|---|---|---|
| Practical | `github.com/OWNER/REPO/issues/N` | A specific public reporter wrote the matching text; **not** a real-world outcome, measurement or buyer request |
| Implementation | `github.com/OWNER/REPO/blob/COMMIT/PATH` | The excerpt occurs in a UTF-8 source file at that commit; **not** compilation, safety, licensing or deployment |
| Academic | `europepmc.org/article/MED/PMID` | The title/abstract excerpt occurs in the publisher-index record; **not** peer-review verification, source entailment or scientific replication |

This routing does not imply every practical observation is a GitHub issue or every academic source is on Europe PMC. Other providers and formats remain **unsupported**, not silently scraped.

The original reasoner and skeptical critic still see all user-provided source text as untrusted data and use the `NONE_ACCEPTED` authority state. A matched source receives an explicit observation receipt in the source-scope annotation, not a qualified graph edge. The existing independent scholarly and institutional search metrics remain separate.

## Live public-source test, not a model-generated fixture

Two public-source packs were assembled from the actual original records in an isolated Optiplex research scratch directory; only **hash-based receipts and URLs** are committed here, not the third-party source bodies.

**Pack 1: food distribution and operational accounting**

- Open Food Network public issue [#14924](https://github.com/openfoodfoundation/openfoodnetwork/issues/14924) and [pinned map service](https://github.com/openfoodfoundation/openfoodnetwork/blob/1167aa7b7585c1794199e032fc15c0e9c1c74104/app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee).
- Foodsoft public issue [#1368](https://github.com/foodcoops/foodsoft/issues/1368) and [pinned order helper](https://github.com/foodcoops/foodsoft/blob/f594be8e64f4d3748d0e418df05fbb554ccce71b/app/helpers/orders_helper.rb).
- Europe PMC [heat-warning threshold abstract, PMID 41622278](https://europepmc.org/article/MED/41622278).
- **5 of 5** submitted passages matched retrieved originals.

**Pack 2: weather API and warning context**

- Open-Meteo user issue [#2229](https://github.com/open-meteo/open-meteo/issues/2229).
- [Commit-pinned Open-Meteo README](https://github.com/open-meteo/open-meteo/blob/5f11eafbf0e4917618870f562bd35f3a40fa240e/README.md).
- The **same** Europe PMC heat-warning abstract.
- **3 of 3** matched retrieved originals.

A separate maliciously altered source-code excerpt falsely claimed multimillion-dollar real customer revenue and global deployment. The actual GitHub source comparison produced **1 text mismatch, 0 matches**, and no authority promotion.

Total: **8 matching source checks across 7 distinct public URLs, and one negative live mismatch test**. The repeated Europe PMC record is *not* counted as independent scientific replication. No source claimed verified outcomes; no payment, program effectiveness, full integration, new source rights or accepted three-layer links were established.

Machine-readable receipts and specific live checked-at timestamps are in `research_materials/opportunity_atlas/public_publisher_source_trial_v1.json`.

## Automated verification

Unit tests use fake public publisher response payloads to check strict URL shapes and family routing, source digest integrity, false pull request IDs, invalid Git blob SHA, wrong MED identifiers, HTML/whitespace matching, publisher outages, tampered user passages and durable controller receipt state.

**Security and deployment boundaries:** The live adapters require working GitHub CLI authentication or Europe PMC network access. Requests are URL-shaped from allowlisted routes; never forward a user URL to `gh api` or an unconstrained fetch. GitHub issue bodies are mutable and a source check is only a point-in-time observation. No local JSON file integrity signature, multi-writer concurrency control, confidential-source authorization, or full scientific review is implemented. Code execution and business qualification remain entirely separate gates.

## What to do next

Extend provider coverage through independently reviewed publisher adapters rather than a generic user-controlled web fetch. Then evaluate calibration of exact-source matching vs meaningful source entailment and compare operator decisions in *previously unseen*, independently sourced multi-sector investigations. Preserve abort/abstain paths; avoid converting source matching into automated claims of effectiveness or economic value.
