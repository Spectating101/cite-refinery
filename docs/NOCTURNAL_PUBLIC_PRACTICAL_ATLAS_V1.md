# Nocturnal → Practical Atlas: publication-gated integration v1

**Scope:** Cite–Refinery's existing three standalone maps. This importer does not create a fourth engine, another installed console script, a private data replica, a cross-layer link or a market ranker.

## Exact source contract

Read the **public snapshot directory** produced by Nocturnal's `src/nocturnal_product/public_snapshot.py`, schema `nocturnal.public_snapshot.v1`. The bridge accepts exactly `manifest.json`, the five public JSONL indexes and `stewardship.json` as its read set. It does not read Nocturnal's `chains/`, source vault, operator journal, case state, local credentials or live API.

Import fails closed unless:
- `publishable=true`, explicit dataset license, source-rights review, approved bounded pilot manifest, zero publication blockers;
- original chain-integrity reports pass and the snapshot contains a chain report;
- every listed public file matches manifest byte length and SHA-256;
- the stable Nocturnal snapshot ID matches the original exporter fingerprint (all six hashes + counts + pilot ID);
- for **nonfictional snapshots**, an out-of-band, independently approved SHA-256 of the exact manifest must be supplied using `--nocturnal-manifest-sha256` (this is an operator trust pin, not a digital signature);
- module-to-matter, module-to-entity, module-to-source and correction references are internally coherent.

The snapshot's own publication approval is a **necessary input**, not proof of truth, ownership of third-party articles or unrestricted reuse. Real-source publication still requires Nocturnal's original legal/editorial gate. Do not copy unreviewed investigation journals into a public atlas.

## What Cite–Refinery adds

- An independent **matter index** with public chronology, institutional stage, actors, literal search and original public source links.
- **Correction reference resolution without adjudication:** the import checks whether a `correction_of` or `supersedes` reference identifies exactly one *approved-public* module (by module ID or event ID) in the same matter. Resolution is annotated as `resolved_same_matter`; missing/withheld, ambiguous, malformed or cross-matter targets remain explicitly unresolved. A resolved pointer means only that a public identifier matched, **not** that the original claim is false, that a dispute was decided, or that an absent reference was deleted. Coverage counts distinguish linked from unresolved correction targets, and timelines expose the resolution. No source body is copied.
- **Literal within-Practical facets:** `--nocturnal-stage`, `--nocturnal-source-domain`, `--nocturnal-evidence-grade`, `--nocturnal-open-dispute`, `--nocturnal-after` and `--nocturnal-before` can be combined with term/matter browsing. Dates match individual published event dates, not inferred case activity intervals; reported grade/dispute/stage are not independently adjudicated. The `--nocturnal-open-dispute` view recognizes Nocturnal's pending states (`submitted`, `under_review`; plus legacy `active`) rather than treating final `corrected`/`upheld`/`rejected`/`withdrawn` as open. Source hostname grouping is not corroboration.
- Immutable module identifiers, correction/supersession links, and a source-file locator `modules.jsonl#L<n>`. Module body is NOT copied into the derived atlas; a text SHA-256 binds its reference to the authorized original snapshot.
- Explicit per-snapshot coverage of matters, source URLs/domains, entities, corrections, missing source links and open dispute flags.
- Incremental comparison with a previously generated Practical map: added modules, unchanged modules and opaque IDs no longer present in the current approved release. **Removed/withheld source text is never carried forward** by Cite–Refinery. A reused module ID with modified original text/content fails closed.
- Clear evidence boundaries: source URL count is not independent corroboration; dispute flags are not adjudicated contradictions; named actors are not guilt findings; the pilot scope is not a world taxonomy; field-level completeness is not claimed.

No new unreviewed classification, LLM conclusion, monetization overlay or Academic/Implementation promotion is created.

## Real two-repository fictional contract run

Use the exact public Nocturnal release generator with its deterministic fictional dataset. **Every subject and .invalid source is invented.**

```bash
# Run inside a checkout of nocturnal-oversight:
PYTHONPATH=. python scripts/ops/build_public_demo_fixture.py \
  --ledger-root /tmp/nocturnal-fictional-ledger
PYTHONPATH=. python scripts/ops/export_public_snapshot.py \
  --ledger-root /tmp/nocturnal-fictional-ledger \
  --output-dir /tmp/nocturnal-fictional-snapshot \
  --pilot-manifest examples/pilot_manifest.fictional.json \
  --dataset-license CC-BY-4.0 --source-rights-reviewed

# Run inside a checkout of cite-refinery:
cite-refinery investigate map-foundations \
  --nocturnal-public-snapshot /tmp/nocturnal-fictional-snapshot \
  --nocturnal-terms Meridian \
  --nocturnal-map-out /tmp/practical.json \
  --json-out /tmp/three_layer.json \
  --markdown-out /tmp/three_layer.md
```

The existing 9 practical abstract reports and 48 TED notices remain distinct from **original Nocturnal public ledger observations**. `--nocturnal-terms` navigates case names, source URLs, entity names, titles and stages, not original body text or semantic embeddings.


# Explore specific evidence dimensions of the *same approved public snapshot*:
cite-refinery investigate map-foundations \
  --nocturnal-public-snapshot /tmp/nocturnal-fictional-snapshot \
  --nocturnal-stage corrected \
  --nocturnal-source-domain local-watch.invalid \
  --nocturnal-after 2025-01-01 \
  --nocturnal-map-out /tmp/practical_filtered.json \
  --json-out /tmp/three_layer_filtered.json \
  --markdown-out /tmp/three_layer_filtered.md

For a real approved release, obtain the exact `manifest.json` SHA-256 from a trusted Nocturnal approval channel, then add `--nocturnal-manifest-sha256 <approved-64-hex-digest>`. A checksum alone cannot prove lawful publication; it prevents unapproved file substitution after an out-of-band review.

To compare a second **approved public** snapshot, pass `--previous-nocturnal-atlas /tmp/practical.json` and use new output paths. The same immutable module in both releases is not new corroboration. Missing previously public modules are flagged as no longer public; Cite–Refinery makes no deletion/retraction claim about why they disappeared.

## Evaluation — independent Practical map first

1. **Source recoverability:** every mapped module has a snapshot ID, module ID, public JSONL locator, immutable body-text digest and source URLs where present.
2. **Institutional process reconstruction:** inspectors can follow a public matter's time-ordered event IDs, status stages, corrections and publication review labels.
3. **Disagreement discipline:** a dispute is a flagged unresolved state; competing external sources have not been compared or semantically adjudicated by the importer.
4. **Coverage humility:** counts describe the *approved snapshot*, not population coverage. The pilot-domain tag is not yet an independently validated field classification.
5. **Safety and synchronization:** unsigned, unapproved, tampered, altered, overwritten or withdrawn material must not be promoted into an apparently current public map.

The Cite–Refinery CI gate runs self-contained fictional integrity/sync fixtures against the documented Nocturnal snapshot contract. **The upstream Nocturnal repository is private**: public Cite–Refinery Actions cannot check it out with their default token. Run the authentic fictional fixture/export through Nocturnal's own authorized checkout (as shown above), then import its publication-approved snapshot in a local authorized environment. This two-repository smoke test has not yet been executed by this PR; do not claim otherwise. No secrets or broader repository permissions are added.

## Follow-on work after this PR

Keep the three-map priority: widen Practical across reviewed non-investigation source classes, deepen Academic claims/methods/contradictions, and run representative original Implementation capability tests. Then assess each map on unfamiliar domains before resuming relations and underconversion discovery.

**Not yet supplied by this PR:** real-world snapshot coverage, independent scientific claim validation, semantic body search, reviewed domain taxonomy, original operator outcomes, independent deployment tests, corroboration analysis, or jurisdictional approval for any particular real-world case.
