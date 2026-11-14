# Global Legal Codex — Milestone 014: Source Vault and Revision-Aware Audit

**Status date:** 15 November 2026. **Implementation:** source-custody infrastructure, reporting-delta test and a subsequently completed **live 8/8 source-byte acquisition and archive import** in a private operator environment. No independent court-signature certification, source-entailment approval, backed-up off-device archive or legal publication clearance.

## Evidence problem solved

Previous Nocturnal capture workflows retained original HTML/PDF bytes only within private GitHub Actions artifacts (30-day expiry). Those are temporary inspection artifacts rather than permanent, authenticated court archives. The 13 November 2026 UK government correction to September Horizon redress reporting also demonstrates why a researcher must preserve source versions and distinguish retroactive corrections from changes in later reporting periods.

### Architecture now implemented

1. Nocturnal bounded real HTTPS source capture and its raw/text identity recheck.
2. Operator-chosen **private persistent vault root** outside temporary Nocturnal case workspaces. An actual authenticated Nocturnal capture copies raw and extracted bytes to content-addressed objects (SHA-256).
3. Append-only sequential, hash-linked event files containing captured source identity, as-of date, file hashes and capture metadata. Reimporting the same real capture is idempotent. Conflicting imports fail.
4. Explicit failed-capture events without fabricated object hashes. Changed webpage text is only an **unreviewed source-delta candidate**.
5. Explicit correction candidate events require old and new exact excerpts in two stored snapshots of the **same source and reference period**. They never automatically become official facts or proof of new/disbursed money.
6. Cite–Refinery custody handoff derives its eight pinned source targets from the pre-existing 012/013 fixtures and requires the actual Nocturnal vault verifier. Synthetic/test records or arbitrary JSON digests cannot be promoted to real capture coverage.
7. A separate Cite reporting-delta evaluator distinguishes a later reference-period observation from a retroactive revision of the earlier published report.

### Eight expected originals

| Family | Sources | Evidence state |
| --- | ---: | --- |
| Milestone 012 | UK Hamilton PDF plus Dutch ECLI 3535 and 3536 | Awaiting genuine verified source-byte archive |
| Milestone 013 | UK MoJ summary, September and October UK redress, Dutch UHT dashboard and ministerial announcement | Awaiting genuine verified source-byte archive |
| Total | **8** | **Fixture-only CI continues to certify zero. Separately, the authorized live operator vault now verifies all eight source-byte captures through the production Nocturnal→Cite bridge.** |

The earlier Milestone 011 institutional sources can be added in a future versioned whitelist after their real capture receipts are separately audited. These eight are not a claim about global source completeness.

## Reporting arithmetic versus revision chronology

All amounts below are official, rounded cumulative GBP millions, not an audit of individual bank transactions:

| Report comparison | Earlier | Later | Meaning |
| --- | ---: | ---: | --- |
| September to October total | 1,727 | 1,756 | +29; a change between reporting-period summaries |
| September to October HSSA | 18 | 18 | No change at million-pound rounding precision |
| 13 Nov correction to old September total | 1,731 | 1,727 | −4; a retrospective published-data correction, **not a clawback** |
| 13 Nov correction to old September HSSA | 22 | 18 | −4; separately corrected series, **not new spending** |

Source: official UK publication list and revision notice:
https://www.gov.uk/government/publications/post-office-horizon-financial-redress-and-legal-costs-data-for-2026

**Old-original gap:** Original September page bytes as they appeared *before* the November correction were not acquired. A later official correction notice must not be presented as a historical original file. Synthetic test snapshots of these amounts are expressly not accepted by the production vault.

## Repository implementation

**Nocturnal draft PR #115:**

- src/nocturnal_engine/legal_codex_evidence_vault.py — append-only hash chain, blob archiving, corruption checking and unreviewed revision tracking.
- scripts/interop/legal_codex_archive_sources.py — operator-only import of completed genuine Nocturnal 012/013 captures, including preflight source/digest/TLS validation.
- tests/test_legal_codex_evidence_vault_014.py — tests for content hash tampering, event sequence gaps, source substitution, injection rejection, missing failure dates, corrections, and archive replay.
- .github/workflows/legal-codex-evidence-vault.yml — isolated Python 3.10 and 3.12 synthetic tests. No original source artifacts are published.

**Cite–Refinery draft PR #143:**

- src/cite_refinery/legal_codex_vault_handoff.py, examples/legal_codex_vault_handoff_014.json and tests/test_legal_codex_vault_handoff_014.py — actual Nocturnal verifier integration and eight-source custody baseline, with zero allowed synthetic source promotions.
- src/cite_refinery/legal_codex_reporting_delta.py and tests/test_legal_codex_reporting_delta_014.py — separates inter-period publication changes from retrospectively corrected entries.
- Existing Legal Codex workflow now also produces the 014 coverage fixture and candidate-only graph, with no fabricated source archive.

## Operator usage (private persistent volume required)

First execute the previously committed bounded Nocturnal capture workflow in an authorized environment and retain its *actual* state directory and matching receipt. Then, from the Nocturnal checkout:

    PYTHONPATH=. python scripts/interop/legal_codex_archive_sources.py \
      --family outcome_013 \
      --state-dir /private/nocturnal-state \
      --receipt-json /private/outcome-013-receipt.json \
      --vault-root /persistent/private/legal-codex-vault \
      --output /private/outcome-013-archive-result.json

Use family judgment_012 with its own case state and receipt for the court originals. This command will refuse fake or unavailable capture bytes rather than fill them from webpages or metadata.

Read-only verification:

    PYTHONPATH=. python -c "from pathlib import Path; import json; from src.nocturnal_engine.legal_codex_evidence_vault import verify_vault; print(json.dumps(verify_vault(Path('/persistent/private/legal-codex-vault')),indent=2))"

Cite custody handoff where Nocturnal is installed in the same authorized Python environment:

    PYTHONPATH=src python -m cite_refinery.legal_codex_vault_handoff \
      examples/legal_codex_vault_handoff_014.json \
      --vault-root /persistent/private/legal-codex-vault \
      --output /private/custody-014-result.json \
      --packet /private/custody-014-graph.json

For reporting deltas:

    PYTHONPATH=src python -m cite_refinery.legal_codex_reporting_delta \
      examples/legal_codex_outcome_trace_013.json \
      --output /tmp/reporting-delta-014.json \
      --packet /tmp/reporting-delta-014-graph.json

## Limits and next acceptance gate

- **Not signed or WORM:** the vault is tamper-evident if historical event head hashes are independently preserved, but it is not a cryptographically signed trust service and an operator with total rewrite access could rewrite all files and hashes. Storage durability, backups, off-vault checkpoints, access control and retention require operational setup outside this PR.
- **Not original legal authenticity:** real publisher bytes and re-extracted text do not certify a court signature, judicial text entailment, source truth or publication permission.
- **Not individual compensation:** UK total paid, UK claims settled and Dutch recognized harmed parents cannot be joined to 2021 Hamilton appellants or the 2019 Dutch litigants without protected source-specific crosswalk records.
- **Not autonomous publication:** all graph relations remain candidates. An independent legal/editorial gate remains required.
- **Not a completed live capture:** as of this handoff, new 014 genuine source ingestion and Nocturnal workflow execution receipts have not been confirmed. The Cite test baseline truthfully reports missing bytes.

**Next gate:** complete off-device backup/restore and independent checkpoint verification, recheck the full UK judicial text and Dutch paragraphs with bilingual legal review, and obtain lawfully accessible individual post-judgment order/payment records. Separately acquire lawful individualized post-judgment orders; do not use national aggregate statistics as substitutes.

Indonesia Chromebook PPK signed appointment and e-catalog order remain unverified; formal PPID requests remain prepared but not sent. Keep both PRs draft.


## Live acquisition and persistent vault addendum — 15 November 2026 (Taiwan)

After the initial fixture-only test, the complete 014 acquisition path was exercised through **real network retrieval and actual production Nocturnal byte/text rechecks** on a connected authorized Optiplex, using isolated temporary repository checkouts rather than modifying an existing development tree. The first run revealed and fixed the native hyphenated case-ID mismatch; independent tests subsequently passed. The judgment-source capture originally failed for two Dutch HTML pages; the implementation was extended with an opt-in, TLS-pinned and entity/DOCTYPE-rejecting official Rechtspraak XML parser, and Dutch ECLI documents were acquired via the judiciary's official XML endpoint. The UK Hamilton PDF capture was corrected to inspect selected opening and operative-disposition pages (not a full-page legal verification).

**Verified live results:** five official 013 reporting pages and three official 012 court source files acquired, giving **8/8** original-source-byte coverage. All captures passed Nocturnal loader integrity checking, were imported into a private operator-controlled local vault outside the temporary test checkout, and were matched by Cite's real `--vault-root` handoff. The private vault contains eight source snapshots and a hash-linked eight-event chain with no synthetic source records. The local vault directory is restricted to 0700 permissions; blob objects were created 0600. No source bytes or private filesystem paths are committed in this public Cite repository.

**Independent suite results:** 34/34 Nocturnal vault/parser tests passed, 252/252 Cite Legal Codex tests passed and the live Nocturnal↔Cite cross-repository contract returned `PASS`. This is not a claim that every Nocturnal general product test ran or that all original-document judicial interpretations were validated.

**Off-vault checkpoint:** a hash-only eight-source inventory and final archive-head digest are committed in Nocturnal's private Git history at `docs/LEGAL_CODEX_VAULT_CHECKPOINT_014.md`. The Git commit is an externally stored hash reference, **not** a digitally signed/witnessed timestamp, WORM guarantee or backup of the source bodies. The latest source data were captured on 2026-11-15 Taiwan time; their authoritative reporting reference periods are earlier and distinct from capture time.

**Important historical correction gap:** the September UK financial page originally published *before* its November revision was **not** archived. Capturing the corrected page does not retroactively establish possession of the earlier version. The September original/correction comparison remains source-attributed to the official notice and not a two-version byte-level proof.

**Remaining gates:** provision an independent, access-controlled backup of the local vault and test restoration; externally verify future checkpoint hashes; review all original judgments (including pages not extracted from the UK PDF) with a qualified legal reader; reconcile individual remedies through lawful original case records; maintain the Indonesia June 2020 signed PPK and purchase-order search separately. The public CI `legal_codex_vault_handoff` fixture intentionally still returns **0 authenticated bytes** because CI does not have access to the private operator archive. No legal publication or liability finding is authorized.
