# Global Legal Codex — Milestone 014: Source Vault and Revision-Aware Audit

**Status date:** 15 November 2026. **Implementation:** source-custody infrastructure and reporting-delta test, not original document acquisition or legal publication clearance.

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
| Total | **8** | **Zero source original acquisitions certified in the fixture-only CI test** |

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

**Next gate:** verify that one live source per jurisdiction can be captured, preserved on a real persistent vault, verified after a second run, and independently anchored. Separately acquire lawful individualized post-judgment orders; do not use national aggregate statistics as substitutes.

Indonesia Chromebook PPK signed appointment and e-catalog order remain unverified; formal PPID requests remain prepared but not sent. Keep both PRs draft.
