"""Read-only, metadata-grounded GitHub portfolio triage.

On purpose, this module neither changes source repos nor attempts to judge
software/claim correctness from GitHub status. Uses existing Atlas project
steering concepts but keeps private portfolio snapshots outside public git.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

SCHEMA = "cite_refinery.portfolio_control.v1"
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HEAD = re.compile(r"^[0-9a-f]{40}$")
NUMBER = re.compile(r"^[1-9][0-9]*$")
Fetch = Callable[[str], Any]


class GitHubReadError(RuntimeError):
    pass


def github_json(endpoint: str) -> Any:
    """Read metadata via the authenticated GitHub CLI. No secrets printed."""
    if not endpoint.startswith("repos/") or any(c in endpoint for c in "\r\n"):
        raise ValueError("unexpected GitHub API path")
    try:
        p = subprocess.run(
            ["gh", "api", "--method", "GET", endpoint],
            capture_output=True, text=True, timeout=35, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GitHubReadError(type(e).__name__) from e
    if p.returncode:
        # Never echo raw stderr: it can contain auth/process details.
        raise GitHubReadError("github_api_nonzero_exit")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise GitHubReadError("non_json_github_response") from e


def check_repo(repo: str) -> str:
    if not REPO.fullmatch(repo) or ".." in repo:
        raise ValueError("repository must be a safe owner/name")
    return repo


def _pull(p: dict[str, Any], repo: str) -> dict[str, Any]:
    num = p.get("number")
    if type(num) is not int or num <= 0:
        raise ValueError("invalid PR number")
    head = p.get("head") or {}
    base = p.get("base") or {}
    sha = head.get("sha")
    if not isinstance(sha, str) or not HEAD.fullmatch(sha):
        raise ValueError("missing PR head SHA")
    url = p.get("html_url")
    expected = f"https://github.com/{repo}/pull/{num}"
    if url != expected:
        raise ValueError("noncanonical PR link")
    return {
        "repo": repo,
        "number": num,
        "url": expected,
        "title": str(p.get("title") or "")[:280],
        "draft": p.get("draft") is True,
        "head": sha,
        "head_ref": str(head.get("ref") or "")[:180],
        "base_ref": str(base.get("ref") or "")[:180],
        "updated_at": p.get("updated_at"),
        "created_at": p.get("created_at"),
        "author": ((p.get("user") or {}).get("login") or ""),
    }


def fetch_open_prs(repos: list[str], fetch: Fetch, max_pages: int = 10) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return projects and errors with explicit completeness markers."""
    projects: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not 1 <= max_pages <= 25:
        raise ValueError("max_pages must be 1..25")
    for repo in list(dict.fromkeys(check_repo(x) for x in repos)):
        project: dict[str, Any] = {"repo": repo, "complete": False, "prs": []}
        projects.append(project)
        try:
            md = fetch(f"repos/{repo}")
            project["default_branch"] = md["default_branch"]
            if not isinstance(project["default_branch"], str):
                raise ValueError("invalid default branch")
            seen: set[int] = set()
            for page in range(1, max_pages + 1):
                raw = fetch(f"repos/{repo}/pulls?state=open&per_page=100&page={page}")
                if not isinstance(raw, list):
                    raise ValueError("invalid pulls page")
                for item in raw:
                    p = _pull(item, repo)
                    if p["number"] in seen:
                        raise ValueError("repeated PR across pages")
                    seen.add(p["number"])
                    project["prs"].append(p)
                if len(raw) < 100:
                    project["complete"] = True
                    break
            if not project["complete"]:
                errors.append({"repo": repo, "type": "pagination_cap", "detail": "PR count is a lower bound"})
        except (GitHubReadError, ValueError, KeyError, TypeError) as e:
            errors.append({"repo": repo, "type": type(e).__name__, "detail": str(e)[:120]})
    return projects, errors


def _ci(repo: str, sha: str, fetch: Fetch) -> dict[str, Any]:
    try:
        raw = fetch(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")
        checks = raw["check_runs"]
        if not isinstance(checks, list):
            raise ValueError("bad check payload")
        if not checks:
            return {"assessment": "no_observed_checks", "checks": [], "limited": False}
        abbreviated = [{
            "name": str(c.get("name") or "")[:100],
            "status": str(c.get("status") or "")[:32],
            "conclusion": c.get("conclusion"),
            "url": c.get("html_url"),
        } for c in checks]
        statuses = {c["conclusion"] for c in abbreviated}
        if any(x in statuses for x in ("failure", "timed_out", "action_required", "startup_failure")):
            state = "observed_failure"
        elif any(x["status"] != "completed" for x in abbreviated):
            state = "checks_pending"
        elif statuses.issubset({"success", "neutral", "skipped"}):
            state = "observed_checks_nonfailing"
        else:
            state = "checks_need_review"
        return {
            "assessment": state,
            "checks": abbreviated,
            "limited": len(checks) >= 100 or raw.get("total_count", len(checks)) > len(checks),
            "note": "Only GitHub check-runs at exact head SHA; NOT complete required-check coverage or verified functionality.",
        }
    except (GitHubReadError, ValueError, KeyError, TypeError) as e:
        return {"assessment": "checks_unavailable", "checks": [], "error_type": type(e).__name__}


def _safe_age(value: Any, now: dt.datetime) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return max(0, (now - parsed.astimezone(dt.timezone.utc)).days)
    except ValueError:
        return None


def build_report(projects: list[dict[str, Any]], errors: list[dict[str, Any]],
                 fetch: Fetch, *, focus: set[str] | None = None,
                 check_limit: int = 12, now: dt.datetime | None = None) -> dict[str, Any]:
    focus = focus or set()
    now = now or dt.datetime.now(dt.timezone.utc)
    all_prs = []
    for project in projects:
        by_branch: dict[str, int] = {
            p["head_ref"]: p["number"] for p in project["prs"] if p["head_ref"]
        }
        for p in project["prs"]:
            q = p.copy()
            default = project.get("default_branch", "")
            dep = by_branch.get(p["base_ref"])
            q["stacked_on"] = (
                f'{p["repo"]}#{dep}' if dep and dep != p["number"] else None
            )
            q["nondefault_base"] = p["base_ref"] != default
            q["age_days"] = _safe_age(p["updated_at"], now)
            q["focus"] = f'{p["repo"]}#{p["number"]}' in focus
            q["review_priority"] = (
                100 if q["focus"] else
                60 if q["stacked_on"] else
                30 if q["nondefault_base"] else
                20 if q["age_days"] is not None and q["age_days"] < 14 else 10
            )
            all_prs.append(q)
    all_prs.sort(key=lambda p: (
        -p["review_priority"], p["age_days"] if p["age_days"] is not None else 100000,
        p["repo"], -p["number"]
    ))
    short = all_prs[:max(10, check_limit)]
    for q in short[:check_limit]:
        q["ci"] = _ci(q["repo"], q["head"], fetch)
        if q["ci"]["assessment"] == "observed_failure":
            disposition = "INVESTIGATE_CI"
        elif q["stacked_on"] or q["nondefault_base"]:
            disposition = "DEPENDENCY_REVIEW"
        else:
            disposition = "ACCEPTANCE_REVIEW"
        q["disposition"] = disposition
        q["rationale"] = (
            "Operator-selected focus; " if q["focus"] else "Metadata-based triage; "
        ) + (
            f'base branch belongs to open PR {q["stacked_on"]}; ' if q["stacked_on"]
            else 'nondefault base branch not matched to an open PR; ' if q["nondefault_base"]
            else "direct base branch; "
        ) + f'exact-head check assessment: {q["ci"]["assessment"]}.'
    for q in short[check_limit:]:
        q["disposition"] = "PENDING_CHECK_EVIDENCE"
        q["rationale"] = "Review priority only; exact-head CI not queried in this run."
    return {
        "schema": SCHEMA,
        "generated_at": now.isoformat(),
        "authority": "READ_ONLY_CANDIDATE_TRIAGE_NO_MERGE_OR_RELEASE",
        "source": "GitHub REST pull list + exact-head check runs via authenticated gh CLI",
        "projects": [
            {"repo": x["repo"], "default_branch": x.get("default_branch"),
             "open_prs_observed": len(x["prs"]), "complete": x["complete"]}
            for x in projects
        ],
        "total_open_prs_observed": len(all_prs),
        "total_count_complete": all(x["complete"] for x in projects),
        "errors": errors,
        "unmatched_focus": sorted(focus - {f'{p["repo"]}#{p["number"]}' for p in all_prs}),
        "next_review": short[:10],
        "all_prs": all_prs,
        "method_limits": [
            "Counts are lower bounds when pagination or API reads are incomplete.",
            "PR branch matching is a dependency lead, not a complete stacked-PR/diff analysis.",
            "GitHub checks can pass while behavior, security, upstream dependencies, or physical/economic claims fail.",
            "No actual code diff review, acceptance decision, or source repo write performed.",
        ],
    }


def _escape(s: Any) -> str:
    return (str(s).replace("|", "\\|").replace("\r", " ").replace("\n", " ")
            .replace("[", r"\[").replace("]", r"\]").replace("<", "&lt;"))[:340]


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Atlas Portfolio Control v1 — Read-only decision brief",
        f'Generated UTC: {report["generated_at"]}',
        "**Authority:** review candidates only; no merges, deployments or operational approvals.",
        f'**Open PRs observed:** {report["total_open_prs_observed"]}' +
            ("" if report["total_count_complete"] else " (INCOMPLETE; lower bound)"),
        "", "## Repository coverage",
        "| Repo | Open PRs seen | Scan |", "|---|---:|---|",
    ]
    for p in report["projects"]:
        lines.append(f'| {_escape(p["repo"])} | {p["open_prs_observed"]} | {"complete" if p["complete"] else "INCOMPLETE"} |')
    lines += ["", "## Ten next PR reviews", "| PR | Last update (days) | Dependency | Exact-head CI | Review disposition |",
              "|---|---:|---|---|---|"]
    for p in report["next_review"]:
        ci = p.get("ci", {}).get("assessment", "not_queried")
        age = p["age_days"] if p["age_days"] is not None else "unknown"
        lines.append(f'| [{_escape(p["repo"])}#{p["number"]}]({p["url"]}) — {_escape(p["title"])} | {age} | {_escape(p["stacked_on"] or ("unresolved nondefault base" if p["nondefault_base"] else "direct"))} | {ci} | {p.get("disposition","pending")} |')
    lines += ["", "## Coverage and limits"]
    if report["errors"]:
        for e in report["errors"]:
            lines.append(f'- {_escape(e["repo"])}: {_escape(e["type"])} ({_escape(e["detail"])})')
    for s in report["method_limits"]:
        lines.append("- " + s)
    if report["unmatched_focus"]:
        lines.append("- Focus references not found among open PRs: " + ", ".join(report["unmatched_focus"]))
    return "\n".join(lines) + "\n"



def read_portfolio_brief(path: Path) -> dict[str, Any]:
    """Read an explicitly selected local snapshot; never access GitHub here."""
    if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("portfolio report unavailable or oversized")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError("invalid portfolio report schema")
    if not isinstance(doc.get("next_review"), list) or not isinstance(doc.get("projects"), list):
        raise ValueError("invalid portfolio report shape")
    return {
        "generated_at": doc.get("generated_at"),
        "projects": doc["projects"],
        "total_open_prs_observed": doc.get("total_open_prs_observed"),
        "total_count_complete": doc.get("total_count_complete"),
        "errors": doc.get("errors", []),
        "next_review": doc["next_review"][:10],
        "authority": "READ_ONLY_CANDIDATE_TRIAGE_NO_MERGE_OR_RELEASE",
    }

def _private_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(data)


def main() -> None:
    cli = argparse.ArgumentParser(description="Atlas read-only GitHub portfolio brief")
    cli.add_argument("--repo", action="append", dest="repos", help="owner/name (repeatable)")
    cli.add_argument("--focus", action="append", default=[], help="operator-prioritized owner/name#number")
    cli.add_argument("--max-pages", type=int, default=10)
    cli.add_argument("--check-limit", type=int, default=12)
    cli.add_argument("--out", required=True, help="private local output directory (not in public repo)")
    args = cli.parse_args()
    if not args.repos:
        cli.error("explicit --repo selections required; private repository names are never shipped in source")
    repos = args.repos
    focus: set[str] = set()
    for item in args.focus:
        if "#" not in item:
            cli.error("--focus must be owner/name#number")
        repo, num = item.rsplit("#", 1)
        check_repo(repo)
        if not NUMBER.fullmatch(num):
            cli.error("--focus must be owner/name#number")
        focus.add(item)
    if args.check_limit < 0 or args.check_limit > 40:
        cli.error("--check-limit must be 0..40")
    projects, errors = fetch_open_prs(repos, github_json, max_pages=args.max_pages)
    report = build_report(projects, errors, github_json, focus=focus, check_limit=args.check_limit)
    root = Path(args.out).expanduser().resolve()
    if any((parent / ".git").exists() for parent in (root, *root.parents)):
        cli.error("--out must be outside a Git working tree to avoid committing private repository metadata")
    _private_write(root / "portfolio.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _private_write(root / "brief.md", markdown_report(report))
    print(json.dumps({
        "brief": str(root / "brief.md"),
        "json": str(root / "portfolio.json"),
        "projects": len(projects),
        "open_prs_observed": report["total_open_prs_observed"],
        "count_complete": report["total_count_complete"],
        "errors": len(report["errors"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
