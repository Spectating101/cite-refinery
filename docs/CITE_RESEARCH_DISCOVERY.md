# Cite research discovery layer

Cite-Refinery separates **literature acquisition** from **literature grounding**.

```text
Nocturnal observations
        ↓
research brief / questions
        ↓
research-discover
Cite deep_research paper acquisition
        ↓
literature_discovery audit
        ↓
research-ground
claim/mechanism grounding and synthesis boundary
        ↓
explicit capability requirements
```

## Why discovery is separate

Finding papers is not evidence that an empirical observation is true, that a mechanism is established, or that an intervention works. The discovery layer therefore records paper-search receipts without creating `rclaim:*` objects or changing observation support state.

Each `literature_discovery` audit preserves:

- the research brief and question provenance;
- the Cite research engine used;
- target paper count and snowball depth;
- per-question status and raw/structured receipts;
- total paper receipts and deduplicated DOI/URL/title keys;
- omitted questions when an explicit question bound is used.

## CLI

When `cite-agent-research` is installed:

```bash
cite-refinery research-discover rproject:... rbrief:... \
  --target-count 30 \
  --snowball-depth 1 \
  --max-questions 4
```

The provider command can be overridden with:

```bash
export CITE_AGENT_RESEARCH_COMMAND="cite-agent-research"
```

If the structured research provider is not installed, the audit records `not_run`; Cite-Refinery does not fabricate a literature set.

## Scale boundary

The TRACE-sized integration contract uses 50 matters / 203 empirical observations, grouped into ten country/domain research briefs. With three bounded questions per brief, the discovery layer issues 30 independent deep-research calls. The test fixture returns two papers per question to verify receipt accounting; it does not claim those synthetic papers are research evidence.

A real full-scale run still depends on Cite-Agent's configured literature sources, API availability, ranking policies, and the quality of the research questions. Acquisition coverage should therefore be measured before requirements are treated as literature-backed.

## Authority rule

`literature_discovery` means **papers were found**.

It does not mean:

- an empirical observation is supported;
- a causal mechanism is established;
- an intervention is effective;
- a capability requirement is justified;
- a Refinery candidate is appropriate.

Those conclusions require subsequent synthesis/grounding and, for software, execution/validation.
