"""Private GitHub collector: source scope, review and temporal comparisons."""
import copy
import io
import json
import os
import stat
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
import test_github_signals as fixture
from cite_refinery.github_private_signals import collect_private, private_to_packet, SCHEMA
from cite_refinery.github_private_signals_cli import main as cli


class PrivateSignalsTests(unittest.TestCase):
    def setUp(self):
        self.fx=fixture.GitHubSignalsTests("test_packet_has_counters_releases_tags_activity_and_source_pinned_dependency")
        self.fx.setUp()
        self.snap=copy.deepcopy(self.fx.capture)
        self.snap.update(schema=SCHEMA,access_scope="restricted_local_private_workspace")
        self.snap["observations"][0]["visibility"]="private"
        for rel in self.snap["observations"][0]["releases"]:
            rel.pop("draft",None)
            rel.pop("name",None)
        self.args=["--db",str(self.fx.db.path),"--project",self.fx.pid,
                   "--manifest",str(self.fx.manifest_path),
                   "--repo-root",str(self.fx.repos)]

    def tearDown(self):
        self.fx.tearDown()

    def packet(self,doc=None):
        return private_to_packet(doc or self.snap,
             project_state=self.fx.db.project_state(self.fx.uid,self.fx.pid),
             project_id=self.fx.pid,manifest=self.fx.manifest,repo_root=self.fx.repos)

    def test_private_packet_source_boundary(self):
        result=self.packet()
        self.assertEqual(result["source_system"],"github_private_signals")
        self.assertIs(result["conversion_metadata"]["public_redistribution_allowed"],False)
        self.assertEqual(len(result["nodes"]),5)
        self.assertEqual(len(result["edges"]),5)
        self.assertTrue(all("restricted_source" in n["tags"] for n in result["nodes"]))
        self.fx.apply(result)
        self.assertTrue(self.fx.db.preview(self.fx.uid,self.fx.pid,result)["already_imported"])

    def test_counter_evolution_without_adoption(self):
        self.fx.apply(self.packet())
        later=copy.deepcopy(self.snap)
        later["observed_at"]="2026-10-20T11:00:00Z"
        later["observations"][0].update(stars=8,forks=1,open_issues=0)
        packet=self.packet(later)
        change=next(n for n in packet["nodes"] if n["kind"]=="comparison")
        self.assertEqual(change["provenance"]["delta"],{"stars":3,"forks":0,"open_issues":-2})
        self.assertIn("not adoption",change["statement"])
        self.fx.apply(packet)

    def test_forged_public_and_other_tenant_rejected(self):
        wrong=copy.deepcopy(self.snap)
        wrong["observations"][0]["visibility"]="public"
        with self.assertRaisesRegex(ValueError,"visibility"):self.packet(wrong)
        with self.assertRaisesRegex(ValueError,"authorized private project"):
            private_to_packet(self.snap,project_state=self.fx.db.project_state(self.fx.uid,self.fx.pid),
                              project_id=self.fx.other_pid,manifest=self.fx.manifest,repo_root=self.fx.repos)

    def test_collector_excludes_draft_and_personal_fields(self):
        def api(slug, endpoint):
            if endpoint=="":return {"full_name":slug,"private":True,"archived":False,
                "default_branch":"main","stargazers_count":3,"forks_count":2,
                "open_issues_count":1,"pushed_at":"2026-10-18T00:00:00Z"}
            if endpoint.startswith("/releases"):
                return [{"tag_name":"unpublished","draft":True,"prerelease":False},
                        {"tag_name":"v1","draft":False,"prerelease":False,
                         "published_at":"2026-10-18T00:00:00Z",
                         "html_url":f"https://github.com/{slug}/releases/tag/v1"}]
            if endpoint.startswith("/tags"):
                return [{"name":"v1","commit":{"sha":self.fx.head}}]
            return [{"sha":self.fx.head,"commit":{"committer":{
                "date":"2026-10-18T00:00:00Z","name":"Person name"}}}]
        with patch("cite_refinery.github_private_signals._github",side_effect=api):
            received=collect_private([self.fx.slug])
        serialized=json.dumps(received)
        self.assertNotIn("Person name",serialized)
        self.assertNotIn("unpublished",serialized)
        self.assertEqual(received["observations"][0]["visibility"],"private")
        with patch("cite_refinery.github_private_signals._github",
                   return_value={"full_name":self.fx.slug,"private":False,"archived":False}):
            with self.assertRaisesRegex(ValueError,"verified private"):
                collect_private([self.fx.slug])
