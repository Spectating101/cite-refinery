"""GitHub public signals, source-pinned dependencies and private import boundaries."""
import copy
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cite_refinery.github_signals import (
    SCHEMA, collect_public, dependency_diff, signals_to_packet,
)
from cite_refinery.github_signals_cli import main as signals_cli
from cite_refinery.hosted_store import WorkspaceDB
from cite_refinery.repository_trend_bridge import manifest_to_packet


def git(root, *args):
    return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL,text=True).strip()


class GitHubSignalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.repos=self.root/"repositories"
        self.repos.mkdir()
        self.slug="ExampleOrg/analytic-core"
        self.local=self.repos/"analytic-core"
        self.local.mkdir()
        git(self.local,"init","-q")
        git(self.local,"remote","add","origin",f"https://github.com/{self.slug}.git")
        (self.local/"README.md").write_text("# Research analytic-core\nVerified provenance documentation for analytic-core\n")
        (self.local/"package.json").write_text(json.dumps({
            "name":"analytic-core","dependencies":{"alpha":"^1.0"},
            "devDependencies":{"test-helper":"~2.0"}}))
        git(self.local,"add",".")
        subprocess.run(["git","-C",str(self.local),"-c","user.name=Test",
                        "-c","user.email=test@example.test",
                        "commit","-qm","initial source"],check=True)
        self.base=git(self.local,"rev-parse","HEAD")
        (self.local/"package.json").write_text(json.dumps({
            "name":"analytic-core","dependencies":{"alpha":"^1.2","beta":"~3.0"},
            "devDependencies":{}}))
        git(self.local,"add",".")
        subprocess.run(["git","-C",str(self.local),"-c","user.name=Test",
                        "-c","user.email=test@example.test",
                        "commit","-qm","modify pinned declarations"],check=True)
        self.head=git(self.local,"rev-parse","HEAD")
        self.manifest={
            "schema":"cite_refinery.repository_portfolio.v1",
            "topics":[{"key":"source_integrity","title":"Repository source integrity"}],
            "repositories":[{
                "repository":self.slug,"directory":"analytic-core",
                "base":self.base,"head":self.head,
                "dependency_files":["package.json"],
                "evidence":[{
                    "key":"provenance","topic":"source_integrity","path":"README.md",
                    "needle":"Verified provenance documentation for analytic-core",
                    "summary":"Repository documents provenance and source integrity",
                }],
            }],
        }
        self.manifest_path=self.root/"manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.capture={
            "schema":SCHEMA,"observed_at":"2026-10-19T10:00:00Z",
            "source":"GitHub public source provider",
            "observations":[{
                "repository":self.slug,"visibility":"public","archived":False,
                "default_branch":"main","stars":5,"forks":1,"open_issues":2,
                "pushed_at":"2026-10-18T09:00:00Z",
                "releases":[{"tag_name":"v1.2","name":"v1.2 release",
                             "draft":False,"prerelease":False,"published_at":"2026-10-18T08:00:00Z",
                             "url":f"https://github.com/{self.slug}/releases/tag/v1.2"}],
                "tags":[{"name":"v1.2","sha":self.head}],
                "recent_commits":[{"sha":self.head,"committed_at":"2026-10-18T09:00:00Z"}],
            }],
        }
        self.snapshot_path=self.root/"captured.json"
        self.snapshot_path.write_text(json.dumps(self.capture))
        dbpath=self.root/"private.sqlite3"
        self.db=WorkspaceDB(dbpath)
        auth=self.db.create_tenant("Testing","owner")
        self.uid=auth["owner_user_id"]
        self.token=self.db.issue_token(self.uid)
        self.pid=self.db.create_project(self.uid,auth["tenant_id"],"Repo signals","Software ecosystem mapping")
        other=self.db.create_tenant("Elsewhere","separate")
        self.other=other["owner_user_id"]
        self.other_pid=self.db.create_project(self.other,other["tenant_id"],"No access","Isolated")
        self.apply(manifest_to_packet(self.manifest,self.repos))

    def tearDown(self):
        self.tmp.cleanup()

    def apply(self,packet):
        p=self.db.preview(self.uid,self.pid,packet)
        self.db.enqueue(self.uid,self.pid,packet,p["project_revision"],p["packet_digest"])
        result=self.db.run_one_job()
        self.assertEqual(result["status"],"succeeded")
        return p

    def packet(self,snapshot=None):
        return signals_to_packet(snapshot or self.capture,
            project_state=self.db.project_state(self.uid,self.pid),project_id=self.pid,
            manifest=self.manifest,repo_root=self.repos)

    def test_exact_pinned_dependency_diff_and_uncommitted_changes_ignored(self):
        changed=dependency_diff(self.repos,self.manifest["repositories"][0])
        self.assertEqual(len(changed),1)
        row=changed[0]
        self.assertEqual([(x["name"],x["spec"]) for x in row["added"]],
                         [("dependencies:beta","~3.0")])
        self.assertEqual([x["name"] for x in row["removed"]],["devDependencies:test-helper"])
        self.assertEqual(row["changed"][0]["before"],"^1.0")
        self.assertEqual(row["changed"][0]["after"],"^1.2")
        original=copy.deepcopy(changed)
        (self.local/"package.json").write_text("UNCOMMITTED MALICIOUS CLAIM")
        self.assertEqual(dependency_diff(self.repos,self.manifest["repositories"][0]),original)

    def test_public_provider_capture_filters_drafts_and_private_sources(self):
        def respond(repo,endpoint):
            if endpoint=="":
                return {"full_name":repo,"private":False,"archived":False,
                        "default_branch":"main","stargazers_count":5,
                        "forks_count":1,"open_issues_count":2,"pushed_at":"2026-10-18T09:00:00Z"}
            if endpoint.startswith("/releases"):
                return [
                    {"tag_name":"INTERNAL","draft":True,"prerelease":False,
                     "published_at":None,"html_url":f"https://github.com/{repo}/releases/tag/INTERNAL"},
                    {"tag_name":"v1.2","name":"v1.2","draft":False,"prerelease":False,
                     "published_at":"2026-10-18T08:00:00Z",
                     "html_url":f"https://github.com/{repo}/releases/tag/v1.2"},
                ]
            if endpoint.startswith("/tags"):return [{"name":"v1.2","commit":{"sha":self.head}}]
            if endpoint.startswith("/commits"):
                return [{"sha":self.head,"commit":{"committer":{"date":"2026-10-18T09:00:00Z"}}}]
            raise AssertionError(endpoint)
        with patch("cite_refinery.github_signals._github",side_effect=respond):
            captured=collect_public([self.slug])
        self.assertEqual(len(captured["observations"][0]["releases"]),1)
        self.assertEqual(captured["observations"][0]["releases"][0]["tag_name"],"v1.2")
        with patch("cite_refinery.github_signals._github",
                   return_value={"full_name":self.slug,"private":True,"archived":False}):
            with self.assertRaisesRegex(ValueError,"not confirmed public"):
                collect_public([self.slug])

    def test_packet_has_counters_releases_tags_activity_and_source_pinned_dependency(self):
        packet=self.packet()
        self.assertEqual(len(packet["clusters"]),1)
        self.assertEqual(len(packet["nodes"]),5)
        self.assertEqual(len(packet["edges"]),5)
        self.assertEqual({e["status"] for e in packet["edges"]},{"qualified"})
        kinds=[set(n["tags"]) for n in packet["nodes"]]
        self.assertTrue(any("published_release" in tags for tags in kinds))
        self.assertTrue(any("git_ref_not_release" in tags for tags in kinds))
        self.assertTrue(any("pinned_git_dependency_declarations" in tags for tags in kinds))
        self.assertTrue(any("bounded_recent_commit_sample" in tags for tags in kinds))
        self.assertFalse(any("deployment_verified" in tags for tags in kinds))
        delta=next(n for n in packet["nodes"] if "pinned_git_dependency_declarations" in n["tags"])
        self.assertEqual(delta["provenance"]["dependency_diff"]["changed"][0]["before"],"^1.0")
        self.assertFalse(delta["provenance"].get("production_ready",False))
        self.assertNotIn("adoption",packet["conversion_metadata"])

    def test_second_observation_yields_bounded_counter_difference_not_adoption(self):
        first=self.packet()
        self.apply(first)
        later=copy.deepcopy(self.capture)
        later["observed_at"]="2026-10-20T10:00:00Z"
        later["observations"][0].update(stars=7,forks=2,open_issues=3)
        second=self.packet(later)
        trend=next(n for n in second["nodes"] if n["kind"]=="comparison")
        self.assertEqual(trend["provenance"]["delta"],{"stars":2,"forks":1,"open_issues":1})
        self.assertIn("not interpretable as adoption",trend["statement"])
        self.assertEqual(len(second["clusters"]),1)
        review=self.apply(second)
        self.assertEqual(review["projected_new_records"]["semantic_clusters"],0)
        self.assertEqual(review["projected_new_records"]["semantic_nodes"],3)
        self.assertEqual(review["new_relation_statuses"],{"qualified":6})
        self.assertTrue(self.db.preview(self.uid,self.pid,second)["already_imported"])
        atlas=self.db.project_projection(self.uid,self.pid)["atlas"]
        self.assertEqual(atlas["summary"]["cluster_count"],3)

    def test_rejects_nonpublic_fabricated_release_origin_and_foreign_project(self):
        bad=copy.deepcopy(self.capture)
        bad["observations"][0]["visibility"]="private"
        with self.assertRaisesRegex(ValueError,"visibility"):
            self.packet(bad)
        bad=copy.deepcopy(self.capture)
        bad["observations"][0]["releases"][0]["url"]="https://example.org/fake"
        with self.assertRaisesRegex(ValueError,"outside exact repository"):
            self.packet(bad)
        bad=copy.deepcopy(self.capture)
        bad["observations"][0]["releases"][0]["draft"]=True
        with self.assertRaisesRegex(ValueError,"draft"):
            self.packet(bad)
        bad=copy.deepcopy(self.capture)
        bad["observations"][0]["stars"]=-3
        with self.assertRaisesRegex(ValueError,"count"):
            self.packet(bad)
        with self.assertRaisesRegex(ValueError,"authorized existing project"):
            signals_to_packet(self.capture,project_state=self.db.project_state(self.uid,self.pid),
                              project_id=self.other_pid,manifest=self.manifest,repo_root=self.repos)
        manifest=copy.deepcopy(self.manifest)
        manifest["repositories"][0]["head"]="0"*40
        with self.assertRaises(ValueError):
            signals_to_packet(self.capture,project_state=self.db.project_state(self.uid,self.pid),
                              project_id=self.pid,manifest=manifest,repo_root=self.repos)

    def test_private_cli_preview_queue_and_credential_and_stale_guard(self):
        args=["--db",str(self.db.path),"--project",self.pid,"--snapshot",str(self.snapshot_path),
              "--manifest",str(self.manifest_path),"--repo-root",str(self.repos)]
        import io
        from contextlib import redirect_stdout,redirect_stderr
        with patch.dict(os.environ,{"CITE_REFINERY_TOKEN":self.token}):
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(signals_cli(["preview",*args]),0)
            report=json.loads(out.getvalue())["review"]
            self.assertEqual(report["projected_new_records"]["semantic_nodes"],5)
            out=io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(signals_cli(["enqueue",*args,"--expected-revision",str(report["project_revision"]),
                                              "--expected-packet-digest",report["packet_digest"]]),0)
            assert self.db.run_one_job()["status"]=="succeeded"
            with redirect_stderr(io.StringIO()):
                self.assertEqual(signals_cli(["enqueue",*args,"--expected-revision","0",
                                               "--expected-packet-digest",report["packet_digest"]]),2)
        with patch.dict(os.environ,{"CITE_REFINERY_TOKEN":"invalid"}):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(signals_cli(["preview",*args]),2)


if __name__=="__main__":
    unittest.main()
