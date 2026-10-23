# Atlas validation gate — 2026-10-24

**Outcome:** Repo-wide CI returned to green without weakening tests. Separate fresh-case preflight passed. **No authenticated live model trials ran** because Desktop Commander reported 0% remaining remote calls on an online Optiplex.

## Executed checks and evidence

1. [Full tests CI run #898](https://github.com/Spectating101/cite-refinery/actions/runs/40007861953): **477 tests, 0 errors/failures, 1 existing skip**. Test backend mocks use an explicit inert agy binary path so validation reaches mocked subprocess assertions; no models called. The full suite installs PyYAML and requests for YAML probes and scientific source clients. This is runner/test dependency correction rather than product semantics modification.
2. [Fresh-case preflight CI](https://github.com/Spectating101/cite-refinery/actions/runs/40008512431): **11 focused tests passed**, including four new prospective preflight checks, plus source-bound three-case `plan` with zero inference.
3. [Existing commercial-blind development CI](https://github.com/Spectating101/cite-refinery/actions/runs/40008512233): **passed**. Not a live run or model preference result.
4. Three fresh precommitted cases occupy `research_materials/opportunity_conversion/blind_casebook_prospective_fresh_v1.json`. Frozen source casebook canonical SHA256: **dec5a367500a9d46d36250546f8d6615ac068c193478a265810dc205443e2efb**. Source documents are separate `fresh-*.json` opportunity cases. They are **not in** `blind_casebook_development_v1.json`.

## Prospective cases (not independently sealed)

| Source-grounded case | Core public evidence | Question / known obstacle |
| --- | --- | --- |
| Homelab Stack Docker integration test bounty | [Original issue #14](https://github.com/illbnm/homelab-stack/issues/14), official [README](https://github.com/illbnm/homelab-stack/blob/main/README.md) | Title advertises $200 while body says $280 USDT; no independent payment/acceptance receipt |
| Local AI registry RTX 5060 Ti recipe | [Original issue #222](https://github.com/sybil-solutions/local-ai-registry/issues/222), official [README](https://github.com/sybil-solutions/local-ai-registry/blob/main/README.md) | At collection the original bounty issue was **closed** and required real GPU + benchmark |
| Tenstorrent typecast uint16 bounty | [Original issue #51655](https://github.com/tenstorrent/tt-metal/issues/51655), official [README](https://github.com/tenstorrent/tt-metal/blob/main/README.md) | $1k listed, open but already assigned to another contributor and requires specialized hardware |

The source sets were selected after earlier **development** evaluations but before any **model trial on these cases**. Authored by the same research team, they are prospective out-of-development inputs only—not independently held out, not random sampling, and not expert-adjudicated ground truth. They must not be presented as external accuracy evidence. Repo notices can change between retrieval and model execution.

## Pending Optiplex real-model execution

Remote Desktop Commander reported **0% remote calls remaining** with Optiplex online. No direct local shell operation, provider model call or judging has happened in this turn.

The runner already supports explicit real inference, with prompts and raw receipts stored privately outside the checkout. On a machine where the user has already authenticated `agy`, after the source casebook is frozen:

```bash
# Zero-inference dry run, confirm frozen source SHA256
python -m cite_refinery.commercial_blind_trial plan \
  --casebook research_materials/opportunity_conversion/blind_casebook_prospective_fresh_v1.json

# ONE smoke case; opt-in, requires authenticated provider (2 candidate calls, 1 independent-family judge)
python -m cite_refinery.commercial_blind_trial run \
  --casebook research_materials/opportunity_conversion/blind_casebook_prospective_fresh_v1.json \
  --provider antigravity --model gemini-3.8-flash-medium \
  --judge-provider antigravity --judge-model claude-opus-5-5-medium \
  --seed 20261024 --max-cases 1 \
  --output /tmp/cite_atlas_fresh_smoke_PRIVATE.json

# Only after valid smoke, same model configurations with all three cases.
python -m cite_refinery.commercial_blind_trial run \
  --casebook research_materials/opportunity_conversion/blind_casebook_prospective_fresh_v1.json \
  --provider antigravity --model gemini-3.8-flash-medium \
  --judge-provider antigravity --judge-model claude-opus-5-5-medium \
  --seed 20261024 \
  --output /tmp/cite_atlas_fresh_full_PRIVATE.json
```

**Cost and methodology boundaries:** Atlas-assisted proposer receives additional deterministic evaluator reasoning, whereas the control does not, even though original public source packets are identical. They do **not** have matched token budgets; no token-billing, procurement revenue, customer willingness to pay, human gold standard, reproducibility across model versions, or independent expert/source entailment checks were collected. The different-family AI judge is not an external human adjudicator.

## No-go / go

- **Ready now:** offline core test suite and independently enumerated fresh-case plan, as an internal research harness.
- **Not yet:** demonstrably superior intelligence, reproducible live model result, human-reviewed blind score or measured cost differential.
- **Do not:** assert paid buyers, convert any advertised reward into sales, deploy to customers, merge the stack solely because CI passed.
- **Later:** execute actual model calls once authorized Optiplex access is available, inspect raw receipts and technical failures, then obtain blinded expert truth review before using scores as evidence for commercialization.

No outreach, job applications, bounty claims, external PR submissions, fund transfers, or bank operations occurred. Draft PR chain is unmerged.
