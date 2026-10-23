# First source-backed Science discovery triage

October 23, 2026. Real public API and pinned public repository README inspection. **Not a Semantic Atlas accuracy benchmark or a new source-corpus expansion.**

## Live run and scope

At PR #114 workflow run https://github.com/Spectating101/cite-refinery/actions/runs/39925893971 the fixed Science API query
`https://science.ecosyste.ms/api/v1/software/search?q=flood&limit=3&after_id=0` returned three metadata candidates, and the candidate-only graph packet contained four neutral nodes (one question + three candidates) and zero accepted claim edges. This is the unfiltered *first page of a literal project/name substring search*, not exhaustive retrieval and not a human-labeled relevance sample.

Manual inspection of each ORIGINAL repository README reveals the following:

| Candidate | Original inspected README Git blob SHA | Source-supported purpose | Suitability for the target river-gauge early-warning use case |
|---|---|---|---|
| `frank1010111/pywaterflood` | `9ad3cbc9c9cbd55bb1a730dd34977c502e8d272f` | Capacitance-resistance models for injection/production well connectivity and waterflood reservoir recovery | **Reject** for river flooding; 'waterflood' is an oil/geothermal recovery term in this repository |
| `floodlight-sports/floodlight` | `15f3246b2d3e8739fcb426f4ff85f97a4ec78c5e` | Sports tracking and event-data analytics | **Reject** for river flooding; name collision |
| `aakashthapa22/Parcel-Level-Flood-and-Drought-Detection-using-AI` | `4ec47ff09d6c728c1bc5fee317f53379b1b4fd3e` | Satellite NDVI/NDWI, Sentinel-1 SAR and mobile imagery for parcel-level flood/drought identification, oriented to insurance | **Adjacent only**: genuine flood detection but neither demonstrated station telemetry warning dissemination nor field integration with our upstream gauge adapter |

These are *investigator-authored review annotations for three observed results*. They are **not** model predictions, blind relevance labels, evidence of technical execution, global Science precision, or data quality estimates. Two are clear query-word false positives relative to our target use; one is genuinely adjacent but unqualified. Do not add these to the sealed Academic holdout or retroactively treat them as an unbiased ranking evaluation.

## Live ORKG blockage

ORKG's public REST `GET https://orkg.org/api/papers` currently returns `HTTP 400` with problem type `orkg:problem:unsatisfied_request_parameter` for all three documented read-only query variants tested in the GitHub job:

- `?title=flood&page=0&size=3`
- `?title=flood&size=10`
- `?doi=10.1145%2F3360901.3364435&size=10`

This is an *observed request compatibility blocker*, not proof the ORKG system contains no relevant papers. Keep the adapter as **code/fixture tested, live blocked**, and investigate updated ORKG endpoint validation before enabling it by default.

## What consolidation actually means

1. Preserve **Science** as a broad read-only **metadata supplier**, not a replacement for Refinery's code-execution validation.
2. Prefer **ORKG** structured research records over building our own paper comparison schema *only when live access and original-source correspondence can be verified*. Until then keep Cite original paper data.
3. Preserve **FollowTheMoney** as a Nocturnal-compatible data modelling reference and local schema-only preview; no publication of private cases or importing identities from merely readable JSON.
4. Use the existing neutral `stage_landscape_packet` format: `DISCOVERED_FOR` candidates, source URL, identity and provider; **no accepted scientific or causal edges**.
5. The next meaningful incremental test is a preregistered 20-item exact-source repo overlap and relevance sample against the frozen Implementation development records, with identical inputs to existing tools and independent adjudication. If Science merely returns metadata, keep it as a lightweight API; do not rebuild its project catalogue.

This illustrates the expected comparative advantage of our authority boundaries—*not* that our AI semantic engine has already outperformed Science, ORKG or an analyst. No code was copied from AGPL Science. The Science dataset's advertised CC BY-SA 4.0 restrictions need review before public redistribution.
