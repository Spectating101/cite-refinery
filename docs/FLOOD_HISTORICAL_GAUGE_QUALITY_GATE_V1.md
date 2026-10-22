# Historical gauge data-quality gate — real observational sample

October 23, 2026. Research and QA only; not a flood alert application.

## Actual public source

Environment Agency flood and river level open data (Beta):
https://environment.data.gov.uk/flood-monitoring/doc/reference

Attribution: This uses Environment Agency flood and river level data from the real-time data API (Beta).

Three readings were preserved in a public third-party mirror, pinned to commit
93728ebdfdda41e629091f9e3550ccf8f2f4c58b:
https://github.com/zenith600/PlymHack-Cybernuts

Selected station: 1502TH, Sandford-on-Thames, England.
Selected measure: 1502TH-level-stage-i-15_min-mASD. **Stage and downstage must
not be combined; flow is a different physical quantity.**

| UTC reading time, February 7, 2026 | Stage mASD | Original mirrored Git blob |
|---|---:|---|
| 13:30 | 0.065 | aaf8ebce8ed0b7989889086bf2aafe8584f81fca |
| 13:45 | 0.062 | af4c08bd913a09b77a7829205c36d857de8a83dd |
| 14:15 | 0.068 | 92924e0c7cee515684dee5560d7a83a28b3defc4 |

The external original snapshots are separately checked byte-for-byte by
the CI job. The mirror is an independent copy, not an authoritative
original Environment Agency API response. Three readings are insufficient
for an actual flood event evaluation.

**Observed sample window:** 13:30–14:15, four nominal 15-minute grid slots,
three archived samples (75% sample presence). The missing 14:00 point in
this mirror is NOT evidence that the live gauge failed, and not an
estimate of original sensor uptime.

## Checks implemented

The Python module flood_historical_gauge_audit.py validates identity,
strict UTC timestamps, actual data units/measure selection, input order,
duplicate times, conflicting duplicate measurements, nonfinite values,
malformed readings and within-sample gaps. It reports descriptive
statistics and an original-reading SHA-256 fingerprint. It refuses to
convert this into real false-alarm, missed-event or warning lead-time
statistics. All those fields are null, as no independently verified
flood-event labels, flood thresholds, warning delivery receipts or local
deployment authorizations have been supplied.

The alternative official-fetch mode requests only one exact original
EA measure over 2026-10-20 through 2026-10-21 using a 2 MB cap,
18-second timeout and no arbitrary URLs. The provider may revise
observations or be temporarily unavailable. If the separate CI job
runs successfully, its actual observed count, sample gaps and raw response
digest are recorded in a review-only artifact. **No observations from
that live query are claimed prior to reading the CI artifact.**

## Repeat locally

    python -m unittest discover -s tests -p 'test_flood_historical_gauge_audit_v1.py' -v

    python -m cite_refinery.flood_historical_gauge_audit \
      --archived-mirror research_materials/runtime_trials/flood_20261023/sandford_archived_ea_sample.json \
      --out /tmp/flood-ea-archive-QA.json

With independently cloned, exact-commit third-party mirror:

    python -m cite_refinery.flood_historical_gauge_audit \
      --archived-mirror research_materials/runtime_trials/flood_20261023/sandford_archived_ea_sample.json \
      --mirror-source-root /path/to/pinned-original-mirror \
      --out /tmp/flood-ea-verified-original-QA.json

Only for a bounded, authorized open-data replay:

    python -m cite_refinery.flood_historical_gauge_audit \
      --official-window 2026-10-20 2026-10-21 \
      --out /tmp/flood-ea-official-two-day-QA.json

## Next evidence gate

To evaluate an actual flood alarm, we still require approved site-specific
gauge datums/thresholds, event-occurrence reference timestamps, and historic
official alarm-issue logs. Those must be independent of predictions.
Detection delay from a synthetic dropout or an arbitrary numerical
threshold is NOT public-warning lead time and cannot measure false
alarms against real floods. Only an offline, time-split, independently
labeled evaluation may proceed, with baseline comparisons and explicit
handling of unknowns. A positive result would not grant authority to
issue real warnings.

Environment Agency warns that its real-time API has no safety-critical
service guarantee. The Atlas must not treat this data stream or the lab
adapter as operational warning infrastructure.

### Separate build issue

The prior full Cite–Refinery test suite is green. The pinned flood replay
CI failed because its original-code NaN ordering gate hard-coded exactly
two wrong permutations across interpreters. The new branch requires at
least one reproduced misranking and reports the actual count; it still
requires correct adapter handling of all six permutations. Python
version-dependent bug frequency is not a physical sensor failure rate.
