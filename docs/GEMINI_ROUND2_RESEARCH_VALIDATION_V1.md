# Second-round evidence validation (isolated replica)

2026-10-20. Original private research workflow: Spectating101/cite-refinery. This document and the adjacent JSON are review material, not accepted scholarly findings.

## Reason for the separate worktree

The existing repository checkout was already on an in-progress cross-study gate branch with several uncommitted files. The original evidence-repair workspace was also already on Round 2, at the source-retrieval stage. Rather than modify another agent's working tree or overwrite a persistent local study, this run created an independent checkout from `c5bfa34` and a copied investigation workspace at `/tmp/refinery-round2-validation-workspace`. The original branch/workspace remain untouched.

## What ran

The original source-repair question was whether observed dog counts during CNVR interventions can be disaggregated into **immigration/abandonment** versus **measurement and visibility changes**. A pre-existing Round 2 source packet supplied scholarly abstracts, bounded full-text excerpts, and real institution-hosted pages. The model did not invent or fetch its own citations.

- **Gemini 3.8 Flash Medium via authenticated Antigravity CLI** performed source-grounded reasoning and produced **11 claims** and **5 cross-source candidate links**. Cite-Refinery's quote and source-ID guard accepted them.
- **Gemini 3.8 Flash High** performed a later, separate skeptical review on the precise supplied passages; 9 claims were marked `entailed` and 2 `partially_supported`; all 5 links were rated `plausible`. These are model labels, not expert gold judgments, independent model agreement, or observed causal validation.
- The second round was staged in the **copied** project graph, with receipt `sgpacket:19ecd3eb69643637`; the bounded two-round controller is now `done` with six unresolved follow-up questions retained as a research backlog. The graph remains in neutral candidate/review states.

### Substantive result and remaining limitation

The most valuable methodology source is a scoping review of free-roaming dog enumeration which documents that **mark–recapture estimates need assumptions about short survey windows, immigration/emigration, lost or misidentified marks, and capture probabilities**. It also notes that transect counts are indicators of abundance, not exact population estimates, with detectability and ownership classification issues. An Arequipa (Peru) study found Google Street View counts correlated with ownership door-to-door surveys in urban communities but were weaker in periurban settings; its reference populations were not identical. This is a direct illustration of measurement dependence on method and geography.

The earlier Jamshedpur (India) observations show increased sterilization coverage with increased observed street counts. Together these sources explain **why higher counts alone cannot distinguish increased actual abundance from altered visibility/detectability, demographic replenishment, or changing survey effort**. They do **not** identify the proportion caused by immigration, abandonment or detectability. A further independent longitudinal dataset with marked individuals or repeated standardized observation effort is required.

The WHO Tanzania project source hypothesizes rapid compensation from culling, whereas academic reviews caution that empirical evidence for an unavoidable vacuum effect is limited; these are **different evidentiary classes**. They may be discussed together as a hypothesis and testable mechanisms, not converted into a claim that immigration caused observed increases. None of this reproduces the author-held Anuradhapura (Sri Lanka) model inputs or geographically matched human-rabies outcomes.

## Audit files

The matching `round2_validation_receipt.json` contains model identities, source URLs and hashes, proposal texts and IDs, review distributions, candidate graph receipt, and boundary statements, without copying complete copyrighted papers or local authentication files.

No merge, deployment, email to authors, accepted-knowledge promotion, or concurrent-workspace rewrite has occurred.
