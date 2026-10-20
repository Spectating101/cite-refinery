# Gemini 3.8 Flash through Antigravity — live Cite-Refinery trial

**October 20, 2026 — experimental; Copilot remains the default inference provider.**

## Verified model access

On authorized Optiplex, the Antigravity command-line app (agy) reports the available model IDs gemini-3.8-flash-low, gemini-3.8-flash-medium and gemini-3.8-flash-high. Its authenticated medium model completed a real structured-JSON inference.

The older installed Gemini CLI, version 0.39.1, rejects its current individual Code Assist authentication and directs the user to Antigravity. The newly installed Copilot launcher copilot-spectator26 also failed its model smoke test with "No supported Copilot prompt model found", while the older Copilot launchers were still quota-limited. Registration is not confirmed serving capacity.

No new API keys or third-party credentials were created or committed.

## Architecture

The Antigravity provider is an explicit opt-in alternative within external_llm_runtime.py. It uses a temporary directory, plan mode, sandbox restrictions, disabled slash commands, model ID validation, bounded --print-timeout and JSON success-envelope parsing. The reasoning prompt prohibits tools. Plan and sandbox modes reduce write capabilities but do not constitute a formal guarantee that the agent has no reading tools. Cite-Refinery alone fetches sources, validates literal quotes and stages graph packets.

Unlike the GitHub Copilot integration, Antigravity is never selected silently as a fallback on quota exhaustion. Copilot continues to be the default on the investigation and adjudication CLIs.

## Real first round on the stored evidence-repair investigation

Original investigation source: Anuradhapura research evidence-repair child 49ecd664b5044b24abfc, originally stuck at the plan stage.

1. Gemini 3.8 Flash Medium selected searches targeting independently measured dog abundance, dog-population turnover and bite/PEP/rabies indicators, without receiving a curated paper bibliography.
2. First source retrieval found irrelevant official WHO pages. A narrow scoped topical guard excluded four of them before reasoning. Gemini replanned institutional searches.
3. The second search eventually retained five public source records: three academic abstracts, one original full-text excerpt from one of those same studies, and one WHO-regional-site policy-focused article on stray dogs in Morocco. Seven irrelevant official pages were excluded across the two attempts.
4. Gemini 3.8 Flash Medium generated eight source-quoted atomic propositions, five semantic candidate links and three questions. Cite-Refinery's exact quote and source-ID validation passed on the submitted propositions. An abstract and a full-text excerpt from the same paper are **not independent experiments**.
5. Gemini 3.8 Flash High performed a separate skeptical inference call. It classified seven propositions as entailed and one uncertain. Among the five bridges, it labeled one plausible, three uncertain and one unsupported. This is **same-model-family** review, NOT scientific replication or cross-model independence.
6. The neutral local graph staged 21 nodes and 28 relationships, with receipt sgpacket:ac64f97281dcd37e. The child now has stage ready_next and three unresolved research questions. There was no change to the original parent's authoritative state.

The substantive finding deserving follow-up is that published Jamshedpur CNVR monitoring reports higher sterilization coverage without establishing a matching decline in absolute street-dog abundance. This generates methodological questions about population turnover and detectability; it does not verify direct impacts on human rabies or reproduce Sri Lankan intervention data. Similarly, a WHO-regional scholarly article is not necessarily official implementation evidence.

Inspect sources, hashes, model judgment counts, topics and the local receipt in research_materials/runtime_trials/antigravity_gemini_20261020/live_receipt.json.

## Reproduce (opt-in)

Select the supported model with the existing CLI:

    cite-refinery-investigate --workspace /tmp/my-investigations step --id YOUR_CHILD_ID --provider antigravity --model gemini-3.8-flash-medium --timeout 180

For the critical reasoning step explicitly select high:

    cite-refinery-investigate --workspace /tmp/my-investigations step --id YOUR_CHILD_ID --provider antigravity --model gemini-3.8-flash-high --timeout 180

The same backend can be used in the existing adjudication and blind benchmark commands with --provider antigravity. It is not a replacement for independent annotators, exact original-data regression replication, or human source audit.

## Remaining boundaries

- Newly registered Copilot remains unavailable for verified inference on the tested host. The Gemini run does not prove Copilot availability.
- Same Gemini model family in Medium and High mode cannot establish model independence.
- A scoped topical exclusion filter is only a basic guard against off-topic papers; semantic evidence assessment remains a separate necessity.
- No geographically matched human-health observations in Anuradhapura were obtained.
- All generated graph relations are neutral candidates or unresolved.
- No automated continuous work, deployment, PR merge, author data request or credentials export happened.
