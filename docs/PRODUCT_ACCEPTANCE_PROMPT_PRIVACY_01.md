# Product acceptance case 01 — Sensitive LLM prompt privacy

**Infrastructure freeze:** tag `infrastructure-v0.24-freeze-20261019`
at Git commit `798a312958f593c6f773a433b8e1f76e18572283`.

This is a **product acceptance case**, not another reusable importer or
hosting layer. The goal is to demonstrate the central Cite-Refinery design:
**problem-specific, source-backed, three-layer semantic modules**, with
reviewed links and explicit, visible knowledge gaps.

## Problem and question

**Question:** Can we map and assess a source-reported user concern about
sensitive information in prompts using independent academic descriptions
of sanitization and an actual bounded implementation evaluation, without
claiming the concern has been resolved?

**Scope:** A single privacy/sanitization cluster. This pilot does *not*
represent a validated systemic privacy incident, a market-wide study,
a fully autonomous academic reviewer, or deployed privacy software.

## Layer 1 — Practical

Source: the existing
`Spectating101/refinery`
Git commit `2b03ad20f8ab3d55462adb38852855b940194c94`,
`evidence/cloakpipe-core-20261016/problem-evidence.json`.

The original public-user post was quoted and reviewed through Refinery's
relation approval flow. The map preserves that attribution and a link to
the original observation. It does **not** verify that any underlying data
leak actually occurred. This distinction is central to the acceptance
criteria.

## Layer 2 — Academic

Two primary-source abstract/intro excerpts and their bibliographic metadata
were manually inspected for topical and methodological scope:

1. Chun Jie Chong, Chenxi Hou, Zhihao Yao, Seyed Mohammadjavad Seyed
   Talebi (2024), *Casper: Prompt Sanitization for Protecting User Privacy
   in Web-Based Large Language Models*, **arXiv preprint**
   https://arxiv.org/abs/2408.07004. The authors describe user-device
   prompt sanitization, including more than rule-only approaches.
2. *ALSA: Context-Sensitive Prompt Privacy Preservation in Large Language
   Models* (2025), **ACM SIGKDD proceedings**, DOI
   https://doi.org/10.1145/3711896.3736840. The abstract concerns
   prompt anonymization with context preservation.

The acceptance input is
`examples/acceptance_prompt_privacy_academic_v1.json`.
It freezes two source URLs, titles, years, publication-status labels,
**short source excerpts**, case interpretations and applicability boundaries.
The case runner checks its complete curated content against a reviewed
SHA256 digest and refuses silent changes to approved claims or quotes.

**Limits:** These are excerpt-based scholarly source representations,
not independently replicated experiments or validated full-text systematic
reviews. Casper is explicitly a preprint; its study results are not assumed
to transfer to CloakPipe. ALSA's method is not represented as a tested
alternative in this case.

## Layer 3 — Program

Source: the actual Git-pinned Refinery CloakPipe experiment package
`evidence/cloakpipe-core-20261016/`, same commit as Practical evidence.

The version-pinned component test recorded:
- 27/27 **required** bounded checks passing;
- 4/4 *broader limitation probes* leaking;
- exact source/build/test receipts and a bounded contract;
- assessment `REUSE_CANDIDATE`, `execution_ready=false`;
- no production admission or general protection demonstrated.

The v0.19 bridge rechecks exact Git objects, receipt hashes, contract/test
consistency, implementation identity and recorded review status. It does
**not** rerun the binary in the acceptance process.

## Actual semantic result

| Evidence family | Nodes |
| --- | ---: |
| Practical | 1 |
| Academic | 4 (2 papers + 2 scoped findings) |
| Program | 6 (capability, implementation, requirement, test, limitation, review) |
| **Total in module** | **11** |

**Five cross-layer links:**
- four **candidate** links: the existing bounded capability-to-problem
  proposal, each scholarly finding-to-reported concern, and the speculative
  ALSA-to-component limitation topical relation;
- one **qualified methodological-scope** comparison between Casper's
  multi-stage approach and the recorded CloakPipe limitation. It explicitly
  does not claim a common test set, comparative superiority or integration.

Every scholarly claim has an additional **qualified DERIVED_FROM** source
attribution edge. Source attribution is separate from proof of a real-world
effect. All citations and limitations remain visible in the module inspector.

Result of the actual private DB + Python gate:
`ACCEPTED_WITH_OPEN_GAPS`.
The 11 nodes represent **structural completeness**, not a solved privacy
problem. The evaluator explicitly refuses to mark this case production ready,
and documents why independent reporter verification, full-text replication,
provider/deployment evidence, comparable experimental populations and a
successful general privacy intervention are all still missing.

## Reproducing the test on the authorized machine

The frozen Refinery Git source commit must be available in the local checkout.
From Cite-Refinery repository root:

    PYTHONPATH=src python3 scripts/acceptance_prompt_privacy.py --refinery-repo /path/to/refinery --sources examples/acceptance_prompt_privacy_academic_v1.json --db /tmp/NEW-private-acceptance-case.sqlite3

This command REFUSES an existing DB path and uses an isolated tenant/project.
It imports only the source-pinned Refinery evidence and the two frozen
operator-reviewed papers through the same private preview/transaction
worker used by other projects. It prints the acceptance report JSON.

Regression tests:

    PYTHONPATH=src python3 -m unittest discover -s tests -q

The tests intentionally try tampering with academic quotes and bibliography,
altering publication status, changing the reviewed case, hiding leakage
failures, promoting unapproved execution, asserting an unproven cross-layer
link, or omitting a source URL. Each must fail review or acceptance.

A separate **actual Chrome** check rendered the isolated real case in the
existing three-column map and inspected Casper's academic source and the
CloakPipe limitation. It reported Practical 1 / Academic 4 / Program 6
and zero browser JavaScript errors.

## Acceptance boundaries and next cases

This case proves we can represent and inspect a genuinely populated,
properly qualified three-layer *module*. It does not prove that any
particular academic paper is applicable to the source reporter's actual
circumstances, nor that any Program solution solves the reported need.

The next product tests should check:
- **External-user comprehension:** can a researcher identify the blocked
  claims and find the evidence in the UI without a developer explaining it?
- **Second unrelated real-world problem:** use a practical domain with
  sufficient independent scholarship *and* a verified Program dataset/tool,
  rather than choosing sources merely to fill three columns.
- **Review governance:** an authorized independent reviewer must approve or
  reject proposed cross-layer applicability, recording justification and
  disagreements explicitly, before any stronger status is claimed.
- **Operational feasibility:** privately host it with scoped authentication,
  retention and source rights only after acceptance, not before.

No new general ingest bridge, automated scheduler or public Vercel deployment
is introduced in this acceptance PR. The previous tag remains immutable.
