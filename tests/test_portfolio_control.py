"""Portfolio Control tests: no GitHub access or source-repository writes."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.portfolio_control import (
    GitHubReadError, _private_write, build_report, check_repo,
    fetch_open_prs, markdown_report, read_portfolio_brief,
)

NOW = dt.datetime(2026, 11, 2, tzinfo=dt.timezone.utc)


def pr(num, *, title="Scope", base="main", head_ref=None, repo="Example/repo",
       sha=None, updated="2026-10-31T00:00:00Z"):
    return {
        "number": num, "title": title, "draft": True,
        "html_url": f"https://github.com/{repo}/pull/{num}",
        "head": {"sha": sha or f"{num:040x}", "ref": head_ref or f"feature/{num}"},
        "base": {"ref": base},
        "updated_at": updated, "created_at": updated,
        "user": {"login": "example"},
    }


def fake_api(*, pulls=None, error_page=None, checks=None):
    pulls = pulls if pulls is not None else [pr(10)]
    checks = checks if checks is not None else {}
    def get(endpoint):
        if endpoint == "repos/Example/repo":
            return {"default_branch": "main"}
        if endpoint.startswith("repos/Example/repo/pulls?"):
            page = int(endpoint.split("page=")[-1])
            if page == error_page:
                raise GitHubReadError("simulated outage")
            a, b = (page - 1) * 100, page * 100
            return pulls[a:b]
        if "/check-runs?" in endpoint:
            key = endpoint.split("/commits/")[1].split("/")[0]
            return {"check_runs": checks.get(key, []), "total_count": len(checks.get(key, []))}
        raise AssertionError(f"unexpected endpoint {endpoint}")
    return get


class PortfolioTests(unittest.TestCase):
    def test_read_only_paginated_inventory(self):
        rows = [pr(i) for i in range(1, 152)]
        projects, errors = fetch_open_prs(["Example/repo"], fake_api(pulls=rows))
        self.assertFalse(errors)
        self.assertEqual(len(projects[0]["prs"]), 151)
        self.assertTrue(projects[0]["complete"])

    def test_incomplete_pagination_fails_openly(self):
        rows = [pr(i) for i in range(1, 152)]
        projects, errors = fetch_open_prs(["Example/repo"], fake_api(pulls=rows, error_page=2))
        self.assertFalse(projects[0]["complete"])
        self.assertEqual(len(projects[0]["prs"]), 100)
        self.assertEqual(errors[0]["type"], "GitHubReadError")

    def test_page_cap_reports_lower_bound(self):
        rows = [pr(i) for i in range(1, 152)]
        projects, errors = fetch_open_prs(["Example/repo"], fake_api(pulls=rows), max_pages=1)
        self.assertFalse(projects[0]["complete"])
        self.assertEqual(errors[0]["type"], "pagination_cap")

    def test_depends_on_existing_open_branch(self):
        rows = [pr(2, head_ref="feature/2"), pr(3, base="feature/2")]
        projects, errors = fetch_open_prs(["Example/repo"], fake_api(pulls=rows))
        brief = build_report(projects, errors, fake_api(pulls=rows),
                             focus={"Example/repo#3"}, now=NOW)
        current = next(p for p in brief["next_review"] if p["number"] == 3)
        self.assertEqual(current["stacked_on"], "Example/repo#2")
        self.assertEqual(current["disposition"], "DEPENDENCY_REVIEW")
        self.assertTrue(current["focus"])

    def test_unknown_nondefault_base_not_assumed_to_be_open_pr(self):
        rows = [pr(3, base="feature/missing")]
        projects, errors = fetch_open_prs(["Example/repo"], fake_api(pulls=rows))
        brief = build_report(projects, errors, fake_api(pulls=rows), now=NOW)
        self.assertIsNone(brief["next_review"][0]["stacked_on"])
        self.assertTrue(brief["next_review"][0]["nondefault_base"])

    def test_exact_sha_failure_is_not_upgradeable(self):
        rows = [pr(7)]
        c = {"0000000000000000000000000000000000000007": [
            {"name": "CI", "status": "completed", "conclusion": "failure",
             "html_url": "https://github.com/example/workflow"}]}
        api = fake_api(pulls=rows, checks=c)
        p, e = fetch_open_prs(["Example/repo"], api)
        brief = build_report(p, e, api, now=NOW)
        self.assertEqual(brief["next_review"][0]["disposition"], "INVESTIGATE_CI")
        self.assertEqual(brief["next_review"][0]["ci"]["assessment"], "observed_failure")

    def test_only_observed_checks_not_global_passing_claim(self):
        rows = [pr(8)]
        c = {"0000000000000000000000000000000000000008": [
            {"name": "focused", "status": "completed", "conclusion": "success",
             "html_url": "https://github.com/example/workflow"}]}
        api = fake_api(pulls=rows, checks=c)
        p, e = fetch_open_prs(["Example/repo"], api)
        report = build_report(p, e, api, now=NOW)
        self.assertEqual(report["next_review"][0]["ci"]["assessment"], "observed_checks_nonfailing")
        self.assertIn("NOT complete required-check coverage", report["next_review"][0]["ci"]["note"])

    def test_titles_escaped_in_markdown(self):
        rows = [pr(9, title="Hello | <bad>\nspoof")]
        api = fake_api(pulls=rows)
        p, e = fetch_open_prs(["Example/repo"], api)
        md = markdown_report(build_report(p, e, api, now=NOW))
        self.assertIn("Hello \\| &lt;bad> spoof", md)
        self.assertNotIn("\nspoof", md)

    def test_bad_repo_and_url_rejected(self):
        with self.assertRaises(ValueError):
            check_repo("bad/../path")
        bad = pr(1)
        bad["html_url"] = "https://evil.example/pr"
        p, errors = fetch_open_prs(["Example/repo"], fake_api(pulls=[bad]))
        self.assertFalse(p[0]["complete"])
        self.assertTrue(errors)

    def test_local_mcp_brief_reads_snapshot_without_network(self):
        rows = [pr(4)]
        api = fake_api(pulls=rows)
        projects, errors = fetch_open_prs(["Example/repo"], api)
        report = build_report(projects, errors, api, now=NOW)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            _private_write(path, json.dumps(report))
            loaded = read_portfolio_brief(path)
            self.assertEqual(loaded["total_open_prs_observed"], 1)
            self.assertEqual(loaded["authority"], report["authority"])
            path.write_text(json.dumps({"schema": "wrong", "next_review": [], "projects": []}))
            with self.assertRaises(ValueError):
                read_portfolio_brief(path)

    def test_local_report_restricted_permissions(self):
        with tempfile.TemporaryDirectory() as t:
            x = Path(t) / "private" / "brief.md"
            _private_write(x, "secret data")
            self.assertEqual(x.stat().st_mode & 0o777, 0o600)
            self.assertEqual(x.read_text(), "secret data")


if __name__ == "__main__":
    unittest.main()
