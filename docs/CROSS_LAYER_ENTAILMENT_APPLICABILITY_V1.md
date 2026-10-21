# Cross-layer entailment and applicability review — October 21, 2026

Successor to Cite–Refinery PR #89, preserving a single canonical investigation lifecycle.

## What was changed

The existing `cite-refinery investigate` command now supports `assess-links`: a **generic three-layer proposed-link review**, not a new research engine or an accepted relationship generator.

The proposal contains exactly three source-grounded anchors—**Practical, Academic and Implementation**—plus explicit problem, mechanism, component claim, desired outcome and an executable/empirical disconfirming test. Each anchor must be a substantial literal quotation from supplied material and must have a separately checked publisher-match receipt in the *same* persisted investigation. The digest, URL, source family and original published text status must agree. Duplicated identities, invented quotations, unverified citations, changed source records and authority-bearing fields are rejected or blocked.

An optional explicitly named model provider can run independent source-to-claim and cross-layer applicability criticism. A model review is a *proposal about semantic fit*, not verification of causal effects, full implementation success, buyer interest or regulatory/legal rights. Every result remains `CANDIDATE_ONLY`; no native accepted graph evidence is promoted.

The critic differentiates three important conditions: a mechanism that is plausibly connected but has no proved solution, a source- or domain-mismatched mechanism, and unresolved semantic fit. It must specify falsification requirements and cannot assert `outcome_supported=true`. Claims of actual executable functionality without an attached runtime receipt are rejected as unverified implementation testing. Incomplete, malicious or schema-invalid model output is retained as a **rejected model-review receipt**, with a content fingerprint, instead of being silently accepted.

## Canonical command

First initialize and `verify-evidence` as documented in PRs #88–89. Then prepare an exact-format JSON link proposal:

```json
{
  "schema": "cite_refinery.cross_layer_proposals.v1",
  "links": [
    {
      "id": "BR-01",
      "practical_problem": "A particular operator-reported map view opens in an unexpected geographic area.",
      "academic_mechanism": "Published geocoding research describes a population of large positional errors.",
      "implementation_claim": "A source file computes map centers using coordinate extremes.",
      "requested_outcome": "A candidate robust view policy might reduce erroneous map center placement.",
      "disconfirming_test": "Test with invalid coordinates and real country-wide map bounds and zoom.",
      "source_anchors": {
        "practical": {"source_id": "USR-P-01", "quote": "An EXACT substantive span from the supplied original issue"},
        "academic": {"source_id": "USR-A-01", "quote": "An EXACT substantive span from a matched scientific source"},
        "implementation": {"source_id": "USR-I-01", "quote": "An EXACT substantive span from the pinned original source file"}
      }
    }
  ]
}
```

The displayed quotes are placeholders; they deliberately will not pass real source validation. Provide exact excerpts from the already authenticated records.

```sh
cite-refinery investigate --workspace /path/to/investigation assess-links \
  --id SESSION_ID --proposals /path/to/links.json

# Optional model-based critical interpretation, never evidence promotion:
cite-refinery investigate --workspace /path/to/investigation assess-links \
  --id SESSION_ID --proposals /path/to/links.json \
  --provider antigravity --model claude-sonnet-5-5-medium
```

Without `--provider`, the command performs source receipt/quotation preflight *only* and returns `publisher_anchors_matched_semantics_unreviewed` or precise failure reasons. It does not claim an entailment verdict. All receipts are stored separately in the same persistent investigator state. The legacy CLI still works; no `pyproject.toml` script was added.

## Live research and adversarial check

Six original public records were retrieved and matched through the source-authentication gate:

- Practical: <https://github.com/openfoodfoundation/openfoodnetwork/issues/14924> and <https://github.com/foodcoops/foodsoft/issues/1368>.
- Academic: peer-reviewed geocoding-error study <https://europepmc.org/article/MED/22469492> and heat-warning study <https://europepmc.org/article/MED/41622278>.
- Implementation: pinned original OFN MapCentreCalculator <https://github.com/openfoodfoundation/openfoodnetwork/blob/1167aa7b7585c1794199e032fc15c0e9c1c74104/app/assets/javascripts/darkswarm/services/map_centre_calculator.js.coffee> and Foodsoft OrdersHelper <https://github.com/foodcoops/foodsoft/blob/f594be8e64f4d3748d0e418df05fbb554ccce71b/app/helpers/orders_helper.rb>.

**All six sources had matching original-publisher passages.** That alone validated *none* of the three proposed links.

The actual Argon initial source-limited review identified one geocoding mechanism as relevant but unverified and two mismatches. Its prompt included named negative-case hints and is **not** an independent blind benchmark. Longer, more relevant matched source passages were then submitted without naming example mismatches in the reviewer instructions. Argon failed at the gateway (CLI exit 3) on that second request. Sonnet 5.5 medium produced a full review, initially rejected by an accidentally too-strict rationale length (the response contained a 1,283-character rationale despite no model instruction limiting it to 1,100). That bound was corrected to 2,200; the **same unmodified model JSON** was revalidated successfully.

Sonnet's final reviewer classifications were:

| Case | Source existence | Semantic/functional decision |
|---|---|---|
| OFN public map error + geocoding error study + original map code | 3/3 authenticated spans | *Mechanistically relevant but semantic/applicability fit uncertain.* Does not demonstrate a working fix or field outcome |
| OFN map error + heat-warning academic study + original map code | 3/3 authenticated spans | *Cross-domain mismatch.* Heat-warning thresholds do not establish map-viewport corrections |
| Foodsoft numerical-ordering problem + geocoding error study + original Ruby helper | 3/3 authenticated spans | *Cross-domain mismatch.* Positional error research does not explain unit conversion precision |

All three are **model criticisms of intentionally authored candidate links**, not human adjudicated gold-standard labels or a statistical benchmark. The unchanged independent source records and reviewer summaries are stored in `research_materials/opportunity_atlas/cross_layer_public_trial_v1.json`. The third-party copyrighted full text and code remain in noncommitted research scratch, not in the repository.

## Critical limitations and next action

- Publisher-passage authenticity is **not** semantic entailment, representativeness, verified field harm, code compilation, licensing or causal effectiveness.
- The geocoding paper studies spatial datasets, not OFN; it is mechanistically relevant but cannot validate the proposed UI remediation.
- The Foodsoft and OFN snippets are source records; their executable-function tests from earlier PRs are **separate evidence**, not silently attached to this gate.
- The proposal cases were selected adversarially with obvious domain separation; this is not a blind, statistically representative generalization score.
- Model responses are advisory and can be invalid or inaccurate. Explicit model availability/error is retained; no account hopping or hidden fallback.
- Local session JSON is not cryptographically signed against privileged local mutation and should not be treated as production-grade chain of custody.
- No accepted scientific claim, product outcome, customer purchase, economic value, upstream change, deployment, or sealed research holdout usage.

Next: bring separately verified functional receipts into this same generic source review through an explicitly typed capability/result attachment; measure human-agreed entailment and abstention over independently chosen unfamiliar problems; then prune duplicated case-specific entrypoints after compatibility audits. **Do not introduce a fourth foundational layer or another standalone workflow.**
