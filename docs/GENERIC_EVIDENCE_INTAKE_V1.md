# General-purpose source intake for the existing investigator

October 21, 2026 — draft successor to PR #87.

This adds **bounded locally supplied evidence**, not a new engine, data layer, domain adapter, console script or LLM adjudicator. The system still has exactly three foundational conceptual layers: Practical, Academic, Implementation. Value capture is downstream, not a fourth layer.

## Canonical use

Create a JSON file using the exact contract below. Its contents are untrusted material submitted by the investigator, **not material automatically fetched or verified by Cite–Refinery**.

```json
{
  "schema": "cite_refinery.supplied_evidence.v1",
  "sources": [
    {
      "id": "USR-P-01",
      "family": "practical",
      "url": "https://example.org/my-field-report",
      "title": "Illustrative local equipment observation",
      "text": "A hypothetical local operator reported that a CO2 sensor reading did not agree with another monitor. This statement has not been independently corroborated.",
      "scope": "Illustrative submitted field note, not a calibrated or independently verified measurement."
    },
    {
      "id": "USR-A-01",
      "family": "academic",
      "url": "https://example.org/academic-methods",
      "title": "Illustrative supplied methods passage",
      "text": "A supplied methodology excerpt describes repeatability testing and the need to distinguish signal calibration from practical ventilation effectiveness.",
      "scope": "Not authenticated against an original paper; no effect size or intervention proven."
    },
    {
      "id": "USR-I-01",
      "family": "implementation",
      "url": "https://example.org/software-repository",
      "title": "Illustrative implementation claim",
      "text": "A submitted repository description suggests an integration path to log CO2 signals without demonstrating a compiled, calibrated, installed or monitored device.",
      "scope": "No repository clone, commit provenance, executable test, hardware test or operator agreement."
    }
  ]
}
```

The example URLs and texts are illustrative. Do not use them as genuine sources.

Initialize and attach through the **existing canonical executable**:

```sh
cite-refinery investigate --workspace /tmp/investigation init \
  --question "How can we verify low-cost classroom CO2 sensing?" \
  --evidence /path/to/evidence.json --max-rounds 1

cite-refinery investigate --workspace /tmp/investigation status --id SESSION_ID

cite-refinery investigate --workspace /tmp/investigation attach-evidence \
  --id SESSION_ID --evidence /path/to/additional-evidence.json

cite-refinery investigate --workspace /tmp/investigation run \
  --id SESSION_ID --provider antigravity --model gemini-4-argon-medium --steps 5
```

A real `run` invokes an authenticated model and independently attempts academic and official retrieval. It is **not** executed in the offline regression tests. The example model identifier is a locally catalog-confirmed identifier from prior Optiplex checks, not a guarantee of current quota.

## Security and correctness boundary

- File input only: no automatic arbitrary URL fetching. URLs are identifiers submitted by the user; HTTPS syntax does not authenticate source contents.
- Exactly 1–6 records per investigation, each with the six required fields, family-consistent IDs (USR-P, USR-A, USR-I), bounded text length, a mandatory scope note and SHA-256 content digest.
- Same ID with changed URL/text is rejected; duplicate URLs under different IDs are rejected within and across ingestions. Repeated identical attachment is idempotent.
- A previous investigation cannot accept new text after the reasoning/critique state begins; start another investigation to avoid stale or silently altered citations.
- Sources are identified as user_supplied_practical_unverified, user_supplied_academic_unverified, or user_supplied_implementation_unverified.
- Source-reasoner **and** skeptical-reviewer prompts explicitly treat submitted material as untrusted data, not instructions or independent corroboration.
- Independent academic/official source coverage is tracked separately from supplied material. Supplied sources do not masquerade as a scholarly abstract or institutional publisher retrieval.
- When at least two supplied documents span at least two families, the investigator may continue **candidate-only review** even if public discovery fails. It must mark missing independently retrieved source families, and all graph nodes remain neutral with edges candidate/unresolved.
- Zero verified field deployment, scientific mechanism, effective intervention, revenue, customer, permission or authoritative graph promotion is established.

## Test matrix

Eight new test functions cover five unrelated illustrative questions (battery recycling, classroom ventilation, cooperative invoicing, flood warning, heat alerts), canonical init/attach/status, idempotence, spoofed privileges, malformed source IDs, duplicate citations, single-source insufficiency and an entirely offline full mocked reasoning/review/graph-stage round.

The same existing controller, review pipeline and CLI handle all these tasks without a new case-specific module. **All user data and search results in these tests are synthetic fixtures**; the tests establish interface generality and failure handling, not accuracy on real unseen sources.

## Known unfinished work

Actual public-source and repository discovery remains separate and incomplete for some real topics. This PR does **not** verify a supplied publisher URL, execute any repository, identify a paying customer or demonstrate live LLM cross-sector performance. Local JSON session files are not tamper-proof or multi-writer transactional. Production ingestion must add authenticated source retrieval, privacy controls, authorization and durable concurrency before accepting consequential evidence.

The next gate is a controlled real-world study over previously unseen topic packs with independently retrieved source verification, integration tests and calibrated abstention metrics. Only then should redundant CLI modules be retired based on behavior-parity checks.
