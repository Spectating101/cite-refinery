# Cite–Refinery semantic capability — frozen Optiplex handoff (2026-10-22)

**Checkpoint state: engineering expansion paused; dedicated live semantic evaluation required.** This is a handoff and pinned source snapshot, **not** a release, branch protection, passing benchmark, production deployment, approved source publication, or merged PR. Avoid new feature development until the actual evaluation provides an evidence-backed reason to continue.

## Exact code baseline

- Repo: https://github.com/Spectating101/cite-refinery
- **Frozen working branch:** `freeze/cite-refinery-semantic-optiplex-handoff-2026-10-22`.
- **Last semantic code commit before freeze:** `5f92c100b86acafc882b3a62eb1984c389a3e784` (PR #108).
- Stacked draft PRs: [#106 offline three-map research browser](https://github.com/Spectating101/cite-refinery/pull/106) → [#107 semantic integration reality audit](https://github.com/Spectating101/cite-refinery/pull/107) → [#108 Academic source-grounded semantic workflow](https://github.com/Spectating101/cite-refinery/pull/108). The stack is **not merged**.
- PR #106's tests and three-map foundation builds **passed** at commit `6748422d5a58fefe437e21a37b4fd951621d7275`. At freeze, #107 at `02c368046ca7a0cbdcf4152b30db7e542f087191` had both CI workflows **queued**, and #108 at `5f92c100b86acafc882b3a62eb1984c389a3e784` had semantic and foundation workflows **queued** and tests **pending**. These may later change; **fetch the current CI results** and do not claim unobserved pass/fail.
- This freeze branch exists to preserve a resumable checkpoint. **Treat it as read-only and do not merge or force-push it.** Develop any repairs in a separate box-agent branch/worktree.

## What actually exists

Three standalone source-backed maps and a 1,497-record offline metadata browser (Practical 57 / Academic 150 / Implementation 1,290). No approved real Nocturnal publication is attached. Academic has a frozen 103-document development source inventory with 66 heldouts sealed; no independently established scientific result. Implementation surveys 1,287 repositories, with only two original source modules executed against 32 synthetic fixtures (31 pass / one reproduced defect), not field-proven functionality.

Earlier model evidence is **separate**: Gemini 23/24 agreement on investigator-authored abstract entailment labels, not independent human gold or the new product's semantic performance. The actual browser's 10 investigator-chosen paired smoke questions retrieved 10/10 source targets with literal words but 0/10 after meaning-preserving paraphrases; this demonstrates a lexical retrieval limitation, **not a blind benchmark accuracy estimate**.

The draft implementation adds `source_grounded_semantic_answer.py` (optional authenticated source→passage→quote→answer→critic flow), `academic_public_text_recovery.py` (recreate original Europe PMC JATS extract with exact full-text SHA match), an optional evidence-checked Academic review dossier in `standalone_workspace.py`, and defensive tests. CI synthetic tests **cannot** establish actual authenticated AI reasoning. Source quote matching establishes quotation existence, **not entailment**.

## Box-agent assignment (run autonomously, through measured conclusion)

**Goal:** determine whether Cite–Refinery can retrieve, interpret and correctly cite permitted *original* research passages with an actual authenticated model, while reliably abstaining from unsupported questions. Run a full integrated evaluation, repair defects in a separate branch, and record the result; do not stop at one passing fixture.

1. **Isolate work**. Fetch the checkpoint branch and create a separate worktree and a fresh agent branch. Leave the frozen checkpoint, other agents' branches and `main` untouched. Do not merge the PR stack just to make local tests run.
2. **Establish technical truth**. Inspect latest #107/#108 CI failures/pending jobs. Run focused tests and the full repository suite; repair source/import/test failures. Prior known #107 audit-fixture bug was missing the three historical Implementation assets (1,494 instead of 1,497); the checkpoint contains the intended fixture repair but it has not been independently verified green.
3. **Recover originals, not replacements**. Build the 103-source Academic Atlas using `build_academic_atlas` on `research_materials/runtime_trials/richer_corpus_20261020/development_source_manifest.json` and `frozen_split_receipt.json`. Recover a bounded public Europe PMC JATS subset through `academic_public_text_recovery.py`. **Only** write `SOURCE_ID.txt` if the exact original extracted-text SHA-256 matches the frozen source record. Track requested/recovered/digest mismatch/unavailable. Do not use, reconstruct, expose or label any of the sealed 66 heldout records.
4. **Invoke the real model**. Run `source_grounded_semantic_answer.py` with an explicitly selected authenticated provider on available original texts (for example a model already legitimately accessible through Antigravity/Copilot, after checking its installed catalog). No quota cycling, silent model fallback, fictitious model output or calling mock responses live. If the provider is unavailable, report this as blocked and preserve the cause without exposing credentials.
5. **Evaluate questions independently**. Before seeing model outputs, freeze an independently judged evaluation set. Include paraphrases without token overlap, source/passage selection, false causal interpretations, negations, contradictions, geographical/population transfer and questions requiring abstention. Track **source retrieval**, **passage relevance**, **citation text integrity**, **substantive evidence entailment**, **unsupported claims**, **abstention**, plus denominator, model identity and latency separately. Exact quote ≠ scientific truth. Use a truly separate model family or reviewer for criticism when available; never call auto-routed unknown models independent.
6. **Validate the product connection**. Reopen the SHA-checked original text and check every quoted character offset when importing optional Academic model receipts. Ensure forged receipts, phantom source IDs, claimed-but-unverified model identities and critic-rejected conclusions cannot become accepted evidence. Rejected model interpretations may be visible only as **explicitly unapproved** review dossiers.
7. **Report and fix**. Save a sanitized `docs/SEMANTIC_LIVE_OPTIPLEX_REPORT.md` in the **agent's work branch** with the actual commands, original source IDs and digest matches, model and provider, pass/fail metrics and raw error examples without restricted source text, proposed repairs, remaining blockers and the exact PR/commit updates. Preserve detailed original texts, account/session data and any sensitive inference artifacts locally. Open a draft repair PR targeting the PR #108 code branch if changes are necessary; do not merge `main`.

### Reproducibility quick start (inside your separate worktree)

```bash
python -m pip install -e ".[server,test]"
python -m unittest discover -s tests -p 'test_semantic_integration_reality_audit_v1.py' -v
python -m unittest discover -s tests -p 'test_source_grounded_semantic_answer_v1.py' -v
python -m unittest discover -s tests -p 'test_academic_public_text_recovery_v1.py' -v
python -m unittest discover -s tests -v
```

Build the frozen Academic Atlas (only local indexed development metadata; no hidden holdout access):

```bash
mkdir -p /tmp/cr-semantic-eval
python - <<'PY'
import json
from pathlib import Path
from cite_refinery.academic_evidence_atlas import build_academic_atlas
p=Path("research_materials/runtime_trials/richer_corpus_20261020")
manifest=json.loads((p/"development_source_manifest.json").read_text("utf-8"))
split=json.loads((p/"frozen_split_receipt.json").read_text("utf-8"))
atlas=build_academic_atlas(manifest,split)
Path("/tmp/cr-semantic-eval/academic.json").write_text(json.dumps(atlas))
print("Academic development source identities:",len(atlas["sources"]))
PY
python -m cite_refinery.academic_public_text_recovery \
  --academic-atlas /tmp/cr-semantic-eval/academic.json \
  --private-out-dir /tmp/cr-semantic-eval/verified-originals \
  --report-out /tmp/cr-semantic-eval/recovery.json \
  --max-sources 8
```

Only after exact original-source recovery and provider checks, invoke the primary model:

```bash
python -m cite_refinery.source_grounded_semantic_answer \
  --academic-atlas /tmp/cr-semantic-eval/academic.json \
  --original-text-dir /tmp/cr-semantic-eval/verified-originals \
  --question "What does the original study actually establish, and what does it not?" \
  --provider antigravity --model gemini-3.8-flash-medium \
  --output /tmp/cr-semantic-eval/answer-review-only.json
```

The above model is an **example configuration**, not confirmation that its authentication, entitlement or model catalog works on Optiplex. Choose the genuinely available authorized backend or record failure.

## Completion / disposition rule

The frozen checkpoint is **not** feature-complete or release-approved. Mark box task **validated** only after there are real source-text SHA matches, successful authenticated semantic inference, independently reviewed adversarial cases, no unacceptable source/citation fabrication, an honest abstention assessment and working preview integration. Otherwise mark **blocked** with specific infrastructure/evaluation defects or **failed** with observed semantic shortcomings. No acceptance of Academic, Practical, Implementation, legal, scientific or commercial evidence is automatic.

**After the box evaluation:** decide KEEP / REPAIR / NARROW before resuming feature expansion. Until then the main portfolio can proceed independently and this snapshot is parked.
