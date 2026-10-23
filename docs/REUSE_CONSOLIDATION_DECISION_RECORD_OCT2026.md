# Three-map OSS reuse consolidation — decision record

**2026-10-23 · Draft research/development branch · Source- and scope-bounded**

The Atlas is **not** three alternative clones of investigative, scholarly, and software-search products. Existing source/discovery/graph systems should be reusable inputs; Cite–Refinery retains original-source verification, source-qualified claims, experimental capability qualification, explicit abstention and decision-receipt governance.

## Original mapped capabilities versus available external implementations

| Map | Existing working internal functionality | Tested external reuse / competing implementation | Decision |
|---|---|---|---|
| Practical / Nocturnal | Native claim/evidence/correction/publication ledger and identity review | OpenAleph investigative documents; FollowTheMoney schema; Nocturnal's own identity adapter already supports `ftm_id`, `opensanctions_id`, and yente candidates under review states | **Do not replace** Nocturnal identity or ledger. Optional schema compatibility only. No imported private people, cases, court or legal-role data |
| Academic / Cite | Frozen 103 development documents + 47 older abstract leads, existing OpenAlex/OpenAIRE metadata discovery, PaperQA2 local sparse candidate passage retrieval (historically successful) | ORKG structured knowledge, OpenScholar and PaperQA2 synthesis | **Keep** native source evidence and passage provenance. PaperQA2 retrieval remains optional. ORKG title-search API returns HTTP 400 (not operational for discovery); do not enable/pretend source support. No local QA inference accuracy established |
| Implementation / Refinery | Frozen 1,287 repository leads, source commit audits and limited original function trials | ecosyste.ms Science / Repos, OpenSSF Scorecard, Zoekt, Software Heritage | **Reuse Science** identity/source metadata where present; keep original function and fit testing. Scorecard/Zoekt are possible future read-only modules, not proof of correctness, local integration, adoption, or permissions |
| Shared semantic/temporal support | Frozen provenance, independent map receipts and promotion gates | Cognee, Graphiti, GraphRAG and LightRAG | **Do not install another knowledge-graph backend without proof**. LightRAG CPU trial previously failed practical indexing-time gate. Temporal/correction integrity remains owned by Nocturnal |
| Funding and commercialization | Candidate opportunity qualification and no-market-proof flags | OpenAIRE research-projects/grants, Science institutional classifications, OpenAlex | **Metadata inputs only**, not promised funding or verified underconversion |

## Actual executed Science source-overlap result

- Original immutable 753 + 605 survey occurrences reconstructed to **1,287 unique, exact GitHub identities** in **44 categories**. Count and category-integrity tests: PASS.
- Fixed, seed-predeclared, category-covered **100-repository sample**, Science `POST /api/v1/projects/bulk_lookup`: **32 single-project identity matches; 68 explicitly unmatched; 0 ambiguous; 0 batch failures; 0 input/result accounting errors**. The category-covered sample is not a probability sample.
- Original source metadata, publication dates, package names, Science scores, institutional matches and Science repository aliases **do not establish** original-code function, scientific validity or field suitability.
- **FULL 1,287-source live census completed successfully** across 52 Science bulk calls: **398 one-project identity matches; 889 explicit nonmatches; 0 multiple-project ambiguities; 0 source/provider failures; 0 missing response identities**. Complete source input SHA-256: `b8bb8c733801c04e8c6f07f0c9a99f4016edd8e677343c93ffe13612aea450d2`. Independently executed full-run receipt: https://github.com/Spectating101/cite-refinery/actions/runs/39928095138 (artifact: `science-full-1287-frozen-repo-reuse-audit`). Direct Science catalog identity overlap is **30.9%**, *not software functionality coverage*.
- Pre-existing first-page Science literal search for `flood` returned two unrelated domain/name matches (oil-reservoir waterflooding, sports analytics) and one adjacent satellite flood/drought-image project, illustrating the danger of name-only retrieval.

Review receipt: https://github.com/Spectating101/cite-refinery/pull/115

## Which code we actually added

- PR #114 provides **read-only provider adapters** for Science and ORKG, local FollowTheMoney-compatible schema/count preview, neutral candidate-packet staging, and a refreshed reuse registry.
- PR #115 adds **frozen 1,287-source exact identity census**, reproducible 100-source cohort, 25-per-batch Science lookup, strict identity and source-batch validation, explicit partial outcomes, and independent Actions audit artifacts.
- **No third-party source code from AGPL Science was copied**. Science's own API data terms advertise CC BY-SA 4.0: record attribution and legal/reuse review before redistribution.
- The source census is not a new research corpus, not a merged core implementation, not an acceptance gate for synthetic model answers or semantic accuracy, and imports neither the 66 Academic heldout identities nor private Nocturnal claims.

## Concrete reuse-first operating rule

A proposed user question should draw from *proven existing systems* first:
1. Practical investigators start with Nocturnal's original and corrected evidence receipts. FollowTheMoney identifiers remain only candidate identity aids. OpenAleph is an optional investigative backend candidate, **not deployed by this pass**.
2. Academic questions start with local source passages and existing OpenAlex/OpenAIRE/PaperQA2 adapters. An external paper's structured graph is not independent entailment.
3. Implementation projects first check registered catalog identities through Science/Repos, then use original Git commits, reproducible negative controls and code-function replays where warranted. A Science absence triggers alternate discovery, not a "no software exists" conclusion.
4. Cross-map opportunity links remain candidate-only until original-source passages, specific implementation requirements, system compatibility, actual adoption barriers and human review warrant stronger statements.
5. Any vendor integration that performs worse than current original modules or substantially increases running cost/permission risk should be removable as an adapter without damaging the Atlas' own evidence system.

## Outstanding gates, without more architecture

- Full census Actions result must pass with interpretable 1,287-source numbers and absence/alias distinction.
- For *paired, representative* subsets of matched/unmatched repositories, measure original source depth, test availability, observed execution success and actual task relevance; compare with ordinary GitHub+AI under the same task and time budget.
- ORKG paper search originally returned HTTP 400 because our generic JSON Accept header selects the legacy controller with different parameter requirements. The v2 Kotlin backend explicitly produces `application/vnd.orkg.paper.v2+json`. A negotiation fix is now committed and awaiting an independent public smoke run; until observed green, keep ORKG optional and Cite's existing sources in place. Never silently treat provider errors as zero scholarly coverage.
- Run Nocturnal private/native publish-only contract with Optiplex; do not bypass its publication approvals through FTM exports.
- Run independent Academic semantic answers and implementation qualification tests; 32 catalog identities are not competitive semantic performance.
- Test favorable adoption/funding hypotheses only after the three maps independently deliver dependable answers.

**Decision:** Proceed with light Science API reuse, preserve PaperQA2/OpenAlex/OpenAIRE and Nocturnal identity investments, keep ORKG/OpenAleph/graph-engine expansion gated, and retain Cite–Refinery's original verification/qualification core. **No blanket claim that the Atlas is superior or that third-party systems have been integrated end-to-end.**
