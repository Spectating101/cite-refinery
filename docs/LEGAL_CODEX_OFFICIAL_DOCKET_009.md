# Legal Codex — Milestone 009: official court-directory corroboration

**Checked 2026-11-10.** Research notes, not a determination of liability.
**Status:** two official *registry entries* located; **zero original judgment PDF bytes acquired, hashed or page-reviewed** in this milestone. The original 2020 signed PPK replacement and specific SD e-catalog order remain absent.

## Direct official court-directory records

| Docket | Named defendant in directory | Decision day | Official entry | Evidence level |
| --- | --- | --- | --- | --- |
| `147/Pid.Sus-TPK/2025/PN Jkt.Pst` | Nadiem Anwar Makarim | 2026-06-30 | [Mahkamah Agung directory](https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf175e3ca8864c4b506313430313034.html) | Official directory metadata; PDF and ZIP downloads **listed**, bytes **not obtained** |
| `148/Pid.Sus-TPK/2025/PN Jkt.Pst` | Ibrahim Arief alias Ibam | 2026-05-12 | [Mahkamah Agung directory](https://putusan3.mahkamahagung.go.id/direktori/putusan/zaf1526c54f13d84ac9f313034373436.html) | Official directory metadata; PDF and ZIP downloads **listed**, bytes **not obtained** |
| `149/Pid.Sus-TPK/2025/PN Jkt.Pst` | Sri Wahyuningsih (from secondary reporting) | 2026-04-30 **reported** | **Specific official page unlocated** | Hukumonline [secondary court reporting](https://www.hukumonline.com/berita/a/melihat-unsur-penyalahgunaan-wewenang-dan-perintah-jabatan-di-putusan-terdakwa-korupsi-chromebook-lt69f34d794ab23/), not official full judgment |

The 148 official summary explicitly says its documentary/electronic evidence was to be used in a separate Sri Wahyuningsih proceeding. This is an **exhibit-disposition cross-reference**, not a verified link between the same 2020 purchase order, not a shared-signature finding and not evidence of shared criminal intent. No court judgment in this milestone is analyzed for legal holdings from its full PDF.

A search-indexed court record is stronger provenance for *case identity, case date and document availability* than Scribd. But indexing does **not** mean the PDF was downloaded and vetted. Access to the official directory may be robot-restricted; do not substitute a third-party mirror while marking it as official custody.

**Live acquisition outcome:** Nocturnal read-only CI run [42845627132](https://github.com/Spectating101/nocturnal-oversight/actions/runs/42845627132) passed its overall capture workflow but received **HTTP 403** for both official 147/148 directory URLs. The attempts are explicitly failed, not captured; their HTML/PDF bytes have not been archived. The workflow's other captured sources do not establish these court originals. Do not evade access controls; request records via official court PPID or approved public download channels.

## Conflicting PPK replacement accounts — precise unresolved questions

1. The prosecutor's 2025 account attributes the 30 June 2020 replacement to refusal/obstruction of a Chrome OS purchase instruction.
2. Hukumonline's 30 April 2026 account attributes to the trial judges a voluntary resignation, health concerns and an influence attributed to M. Ihsan, and says the successor had procurement certification while the e-catalog deadline approached. It reports criticism of the rushed appointment and missing written handover.
3. **These descriptions are neither equivalent nor automatically mutually exclusive in every detail.** Voluntary signing does not establish freedom from pressure; a procedural flaw does not establish procurement illegality or individual criminal liability. The official 149 reasoning, contemporaneous resignation and successor's actual decree are needed.

## Recovery sequence — separate three evidence levels

**Judicial-original tier**: locate official 149 trial directory and request its authenticated decision; obtain actual 147 and 148 directory-linked PDF/ZIP bytes through authorized public channels. Record HTTP retrieval/source URL, retrieval timestamp, SHA-256, PDF signature/watermark if any, page count, and page-anchored legal reasoning/exhibit indexes. Do not mark complete solely on a URL or snippet.

**Administrative-original tier**: ask PPID Kemendikdasmen for `15004/C3/KPA/VI/KP/2020` with annexes **without presuming it names the June 30 successor**, and for the contemporaneous June 30 PPK resignation/termination, replacement decree, KPA authorization, and handover (or a written no-record reply).

**Transaction-original tier**: ask LKPP and competent ministry custodians for the **SD** 30 June electronic catalogue order and audit trail including transaction/package IDs, unit, initiator vs PPK approval, creation/approval/cancellation timestamps, supplier, line items and signed purchase order. The **SMP** addenda `3535/C4/LK/2020` and `3945/C4/LK/2020` are separate November documents; do not merge them into the June SD transaction.

Acceptance: *court registry page verified* != *judgment PDF original acquired* != *2020 signed procurement instrument acquired*. All evidence edges remain candidate-only until records are obtained and independently reviewed.

## Code and nonclaims

- `examples/legal_codex_official_docket_009.json` holds the three separately attributed case locators and one limited cross-case reference.
- `src/cite_refinery/legal_codex_docket_registry.py` refuses fake official host/path, invented PDF custody, invented procurement identity and inferred joint liability.
- `tests/test_legal_codex_official_docket_009.py` exercises those gates.
- Prior milestone 008's counts and records remain intact, with no silent promotion.

Run:
```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_legal_codex*.py' -v
PYTHONPATH=src python -m cite_refinery.legal_codex_docket_registry examples/legal_codex_official_docket_009.json --output /tmp/official-docket-009.json --packet /tmp/official-docket-009-graph.json
```

**Formal PPID requests have not been submitted.** They require identity/eligibility details from the legitimate applicant; none were supplied or fabricated.
