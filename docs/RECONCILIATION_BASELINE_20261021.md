# Cite–Refinery integration baseline — October 21, 2026

This branch is **not deployed**, and it does not mutate main. It reconciles the consolidated Argon source baseline with our four previously unmerged development increments.

## Verified ancestry and preservation

- Parent consolidated origin/main: b9a37c6, with 420 passing tests.
- Four source commits replayed on a fresh branch: 304b6b3, c289b82, f292162, d503afe.
- Replayed local commits: fc8ef22, 3da0273, 6551049, d7e62f3.
- First cherry-pick conflict was in pyproject.toml, where Argon's competitive gate and the repair-replace entrypoint used the same line. Both are preserved.
- **441 tests passed** and Python wheel packaging succeeded.
- Byte-for-byte Git blob comparisons: all four later research result JSON files and their four corresponding implementation modules match the original later feature branch exactly.
- Argon's competitive gate code and tests match origin/main exactly.
- The integrated project retains **50 registered console entrypoints**; this is an architectural debt measure, not an optimization achievement.
- Both old worktrees and all previous draft PRs remain preserved.

## What this does not show

Regression retention is not completion of OFN's full browser/instance integration, Foodsoft's full Rails/database suite or a commercial opportunity. Existing source and rights limitations remain intact. No production deployment, external maintainer contact or accepted graph authority change follows.

## Next-cycle engineering rules

1. No more case-specific core modules and console entrypoints without a generic capability need.
2. Expose the existing InvestigationController through the canonical cite-refinery CLI, keeping old entrypoints compatible.
3. Test the generic interface with previously unseen problem statements, reporting missing Practical or Implementation source families explicitly.
4. Consolidate overlapping module clusters and entrypoints based on caller/dependency audits and behavioral parity, not a target file count.
5. Separately validate real operator utility and economic demand; do not infer it from GitHub issue existence or model consensus.

This is a safe integration staging branch. Main is untouched, prior worktrees remain intact, and final merge is not presumed.
