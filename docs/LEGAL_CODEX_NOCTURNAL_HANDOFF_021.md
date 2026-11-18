# Legal Codex 021 — portable candidates for native Nocturnal intake

This exporter connects the source-bound **020 remedy tracker** to a portable
private intake format. It does not create an intervention verdict, infer that a
court order was performed, or approve publication.

The actual 020 inputs produce **four public decisions, twelve independently
scoped components, and twenty-seven source-bound events**. Three components
carry explicit public-source findings of fulfillment. The underlying medical
and taxpayer records are not held by this project. The Finnish decision remains
`not_final_as_published`, and its inconsistent interval descriptions remain
visible review flags.

## Build and verify

```bash
PYTHONPATH=src python -m cite_refinery.legal_codex_nocturnal_handoff \
  --dutch-evidence-dir evidence-020/dutch \
  --finlex-evidence-dir evidence-020/finlex \
  --ledger examples/legal_codex_remedy_020.json \
  --as-of 2026-11-18 \
  --output legal_codex_021_handoff.json

PYTHONPATH=src python -m cite_refinery.legal_codex_nocturnal_handoff \
  --verify legal_codex_021_handoff.json \
  --expected-sha256 <packet_sha256-from-the-selected-export>
```

The builder calls the existing 020 receipt and source loaders. Validation works
offline from the portable packet: it re-extracts each embedded original XML
body against the reviewed source pin, verifies the saved extraction, and
recomputes the remedy report from its curated input ledger. It does not accept
an independently edited report as the basis for a handoff.

Python entry points are:

```python
build_handoff(dutch_folder, finlex_folder, ledger_path, as_of)
validate_handoff(packet, expected_packet_sha256=None)
read_packet(path)
```

The optional expected digest binds a previously selected version. Native intake
should require it as an explicit operator input. It is not a signature or proof
that an analyst's reading of a source is correct.

## Portable contract

The schema is `legal_codex.nocturnal_handoff_021.v1`.

| Field | Meaning |
| --- | --- |
| `packet_id`, `packet_sha256` | Deterministic packet version identity and canonical JSON body digest. |
| `as_of` | The requested evidence cutoff used by 020. |
| `boundaries` | Fixed candidate status, no original claimant-record custody, no intervention verdict, no publication authority, and no independent legal review. |
| `input_ledger`, `input_ledger_sha256` | Visible, curated 020 source bindings, component definitions and events, sufficient to recompute the exported state. |
| `sources` | Original public XML bytes, exact extracted documents, capture metadata and source-version information. |
| `components` | Complete 020 component report rows, preserving component IDs and scope. |
| `events` | Complete visible 020 event rows, preserving event IDs, component IDs, kinds, roles, source anchors and dates. |
| `counts` | Source, component, event and public-source-confirmation counts. These are not accuracy or success rates. |

Each source retains the 020 source report fields (`source_id`, `identity`,
`source_url`, `raw_sha256`, `source_date`, `available_on`, `availability_basis`,
`publication_basis`, `historical_version_verified`, `visibility_note`, and
`decision_finality`) plus:

- `format`, `captured_at`, `raw_bytes`, and `raw_content_base64`;
- `extracted_document`, with original `{id, text, sha256}` blocks, and
  `extracted_sha256`;
- `capture_receipt_schema`, the original per-source `capture_receipt`, and
  `capture_receipt_sha256`;
- `extraction_scope`, including the Finnish extraction's numbered-paragraph
  limitation. Unnumbered continuations remain in the complete raw XML.

The original four XML bodies total **152,302 bytes**. The packet retains them;
the consumer need not fetch a possibly changed version to resolve an anchor.
Capture receipts record the earlier fetch process. They are not signed
attestations, and importing them is not a new live acquisition.

Canonical JSON uses Python-equivalent UTF-8 serialization with
`sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, and
`allow_nan=False`. The packet digest covers every field except `packet_id` and
`packet_sha256`. The ID is `legal-codex-021-` followed by the first 24 hex
characters of that digest. `extracted_sha256`, `input_ledger_sha256` and
`capture_receipt_sha256` use the same convention for their complete objects.
An extracted-document digest is therefore a content digest, not a hash of a
particular pretty-printed JSON file.

## What a native projection must preserve

The appropriate native form is **four private candidate cases**, with one note
per component: two, four, two and four notes respectively. Keep the full packet
as private provenance. A note's English interpretation and state must remain
distinguishable from its exact original-language source excerpts. Preserve all
twenty-seven events in provenance even where several events support one note.

Order, receipt, adequacy and fulfillment are separate fields. The 2026 hospital's
prior log receipt must not close its later explanation order. The ministry's
new decision is not a verified receipt. A reversal of the staff-identity
requirement does not reject all access. Finland's decision not to issue a
further unavailable-record order is not a finding that the earlier request was
fulfilled. Penalty authority does not imply accrual or payment.

The native source entry should retain the original XML blob and use an explicitly
named XML text projection whose excerpt offsets can be revalidated against the
raw body. Keep the original capture timestamp separate from the native import
timestamp. The as-of date, judicial decision date, source production date,
public-availability basis and import time have different meanings.

Do not route this material through an intervention-verdict endpoint. Public
judgment observations are research candidates. Existing native source review,
independent editorial research, staging and release decisions remain separate
operations; the packet supplies none of those approvals. Modified candidates
are new versions and require fresh review.

## Verification boundaries

The exporter rejects source changes even when an envelope's hashes are
recomputed, because the public XML must still match the reviewed raw pin and
re-extraction. It also rejects wrong-case event bindings, edited event quotes,
fabricated projected fulfillment, altered finality, removed discrepancy flags,
duplicate source identities, missing projected events, and promoted boundary
flags. Before the evidence cutoff contains a visible event, it produces no
intake packet. Future components and deadlines are not copied into an earlier
visible projection.

This validates custody, internal consistency and factual scope rules; it does
not automatically establish the legal meaning of a curated annotation. A new
validly hashed analyst ledger can still be a new unreviewed interpretation.

Run the actual-source exporter checks with:

```bash
PYTHONPATH=src \
LEGAL_CODEX_020_DUTCH=evidence-020/dutch \
LEGAL_CODEX_020_FINLEX=evidence-020/finlex \
python -m unittest discover -s tests -p 'test_legal_codex_nocturnal_handoff_021.py' -v
```

Source-dependent checks skip if their real inputs are absent. An integration
job should provide them and reject skipped checks. Native Nocturnal import,
journal reload, source review and workflow results require their own end-to-end
verification; passing the exporter suite alone does not establish them.

The dedicated `legal-codex-nocturnal-handoff-021` workflow acquires all four
original public decisions and runs three explicitly separate test groups: the
four standalone 019 literal/reference/admission checks, all 020 checks, and all
021 export checks. Each group must pass with zero skips. The full 019
institutional-page regression remains in its existing dedicated workflow; this
job does not fabricate its historical failed lead receipt or claim to rerun that
acquisition. The artifact includes source receipts, original bodies, the portable
packet, test counts and validation outcomes, including partial/failure outcomes.
Its report explicitly records that native Nocturnal import and model review were
not executed in this Cite-only job.
