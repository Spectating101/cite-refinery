# Atlas Portfolio Control v1 — read-only execution

Status: experimental; draft stacked on Atlas PR #130.

## Scope and operation

This extends the existing development-steering capability with a read-only GitHub PR metadata adapter. It does not replace project registries or source journals, create issues, merge PRs, deploy, schedule agents, or alter source repositories.

Requires an authenticated GitHub CLI. Explicitly choose repositories and an output directory outside any Git working tree. Example:

    PYTHONPATH=src python -m cite_refinery.portfolio_control --repo OWNER/REPO --focus OWNER/REPO#123 --out ~/.local/share/atlas-portfolio-control/private-run

Output:
- portfolio.json: metadata for observed PRs and review candidates.
- brief.md: human-readable current decision brief.

Output files are private owner-only. Neither private repository names nor their reports are committed to Atlas source.

Optional local stdio MCP: set CITE_REFINERY_PORTFOLIO_REPORT to the absolute private portfolio.json path and run the existing cite_refinery.headless_mcp. This is a trusted-user local tool, not a public endpoint.

## Limits and trust boundaries

- GitHub API is queried through read-only GET requests; 100 PRs per page, bounded pagination; incomplete counts are explicitly labeled.
- Open stacked branches are matched by exact base/head branch refs. An unmatched nondefault base remains unresolved; actual code dependencies can be more complicated.
- For selected candidate PRs, check runs are queried by exact head SHA. Passing checks are only observed checks, NOT required-check completeness, correctness, security, or release readiness.
- Candidate review order prefers explicitly named focus PRs then recent or stacked work; priority is not a proven value score.
- GitHub PR titles are untrusted metadata; no instructions embedded in them are executed. Markdown output escapes the untrusted text.
- INVESTIGATE_CI can mean code, dependency, runner, quota or billing trouble. Human review of exact runs is required.
- No merges, deployments, private-data publishing or new source contact are authorized by this implementation.

## Validation

    PYTHONPATH=src python -m unittest discover -s tests -p 'test_portfolio_control.py' -v
    PYTHONPATH=src python -m unittest discover -s tests -p 'test_development_steering.py' -v
    PYTHONPATH=src python -m unittest discover -s tests -p 'test_headless_intelligence.py' -v

First real Optiplex execution (November 2, 2026) scanned six selected repositories and observed 401 open PRs with full pagination, zero API errors, and ten checked review candidates. The actual snapshots remain on the private local computer; CI uses synthetic fixtures only.

## Next acceptance gate

Inspect actual diffs, exact CI run logs, root causes and upstream dependencies for the ten candidates. Ask project owners to accept, consolidate, park or supersede. Add independently supported effort/economic priority before claiming automated portfolio planning.
