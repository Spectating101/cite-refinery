"""Pinned repository evidence, Git history and private project import controls."""
import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cite_refinery.hosted_store import WorkspaceDB
from cite_refinery.repository_trend_bridge import manifest_to_packet
from cite_refinery.repository_trend_cli import main


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL, timeout=15
    ).decode().strip()


class RepositoryTrendBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.checkout = self.root / "repos"
        self.checkout.mkdir()
        self.config = {
            "schema": "cite_refinery.repository_portfolio.v1",
            "topics": [{"key":"source_provenance","title":"Source provenance and review"}],
            "repositories": [],
        }
        for idx, name in enumerate(("project-one","project-two")):
            repo = self.checkout / name
            repo.mkdir()
            git(repo, "init", "-q")
            git(repo, "remote", "add", "origin",
                f"https://github.com/Spectating101/{name}.git")
            doc = repo / "README.md"
            marker = f"{name} records its evidence authority and provenance"
            doc.write_text("# Research\n" + marker + "\n", encoding="utf-8")
            git(repo, "add", "README.md")
            self._commit(repo, "record first documented capability")
            base = git(repo, "rev-parse", "HEAD")
            (repo / "evidence.md").write_text("Change tracked in committed source.\n")
            git(repo, "add", "evidence.md")
            self._commit(repo, "add evidence log")
            head = git(repo, "rev-parse", "HEAD")
            self.config["repositories"].append({
                "repository": f"Spectating101/{name}", "directory": name,
                "base": base, "head": head,
                "evidence": [{
                    "key": "provenance_note", "topic": "source_provenance",
                    "path": "README.md", "needle": marker,
                    "summary": f"{name} documents evidence authority and provenance",
                }],
            })
        self.dbfile = self.root / "private.sqlite3"
        self.db = WorkspaceDB(self.dbfile)
        identities = self.db.create_tenant("Portfolio Test", "owner")
        self.owner = identities["owner_user_id"]
        self.token = self.db.issue_token(self.owner)
        self.viewer = self.db.add_user("viewer")
        self.db.grant_membership(self.owner, identities["tenant_id"], self.viewer, "viewer")
        self.viewer_token = self.db.issue_token(self.viewer)
        self.project = self.db.create_project(self.owner, identities["tenant_id"],
                                              "Repository portfolio", "Map changed projects")
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps(self.config))

    def tearDown(self):
        self.tmp.cleanup()

    def _commit(self, repo, msg):
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=Test",
             "-c", "user.email=test@example.org", "commit", "-qm", msg],
            check=True,
        )

    def _packet(self):
        return manifest_to_packet(self.config, self.checkout)

    def test_pinned_program_evidence_and_candidate_crossrepo_topic(self):
        packet = self._packet()
        self.assertEqual(len(packet["clusters"]), 2)
        self.assertEqual(len(packet["nodes"]), 6)
        self.assertEqual(len(packet["edges"]), 5)
        self.assertEqual(
            {node["layer"] for node in packet["nodes"]}, {"program"}
        )
        self.assertEqual(
            [node["kind"] for node in packet["nodes"]].count("event"), 2
        )
        capability_nodes = [n for n in packet["nodes"] if n["kind"] == "capability"]
        self.assertEqual(len(capability_nodes), 2)
        for node in capability_nodes:
            self.assertIn("#L2-L2", node["source_refs"][0])
            self.assertEqual(node["provenance"]["line_start"], 2)
            self.assertIn("verbatim excerpt", node["provenance"]["verification_scope"])
        links = [edge for edge in packet["edges"] if edge["relation"] == "RELATED_TO"]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["status"], "candidate")
        trends = [n for n in packet["nodes"] if n["kind"] == "event"]
        self.assertTrue(all(n["provenance"]["commit_count"] == 1 for n in trends))
        self.assertTrue(all("not_market_adoption" in n["tags"] for n in trends))

    def test_operator_cross_layer_candidate_to_exact_project_node(self):
        # Add a prior Practical node: the Program mapping may nominate it, but
        # only an explicit candidate relation can be created.
        prior = {
            "schema":"cite_refinery.semantic_graph.v1",
            "source_system":"nocturnal",
            "clusters":[{"key":"observed_problem","title":"A specific observed problem"}],
            "nodes":[{"key":"problem_observation","statement":"Observed lack of data custody",
                      "kind":"observation","layer":"practical","clusters":["observed_problem"]}],
            "edges":[],
        }
        preview=self.db.preview(self.owner,self.project,prior)
        self.db.enqueue(self.owner,self.project,prior,0,preview["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")
        state=self.db.project_state(self.owner,self.project)
        target=next(n for n in state["semantic_nodes"].values() if n["layer"]=="practical")
        config=copy.deepcopy(self.config)
        config["problem_links"]=[{
            "repository":"Spectating101/project-one",
            "evidence_key":"provenance_note",
            "target_node_id":target["id"],
            "relation":"ADDRESSES",
            "rationale":"An operator proposes that the documented custody infrastructure is relevant to this observation",
        }]
        mapped=manifest_to_packet(config,self.checkout,project_state=state,project_id=self.project)
        links=[e for e in mapped["edges"] if e["relation"]=="ADDRESSES"]
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]["target"],target["id"])
        self.assertEqual(links[0]["status"],"candidate")
        self.assertEqual(mapped["conversion_metadata"]["proposed_cross_layer_links"],1)
        # Ingestion preserves an unresolved Program-to-Practical relationship.
        review=self.db.preview(self.owner,self.project,mapped)
        self.assertEqual(review["projected_new_records"]["semantic_edges"],6)
        self.db.enqueue(self.owner,self.project,mapped,review["project_revision"],review["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")
        state=self.db.project_state(self.owner,self.project)
        edges=[e for e in state["semantic_edges"].values() if e["relation"]=="ADDRESSES"]
        self.assertEqual(len(edges),1)
        self.assertEqual(edges[0]["status"],"candidate")

    def test_cross_layer_rejects_wrong_tenant_node_and_unapproved_relation(self):
        config=copy.deepcopy(self.config)
        config["problem_links"]=[{
            "repository":"Spectating101/project-one",
            "evidence_key":"provenance_note",
            "target_node_id":"sgnode:nonexistent",
            "relation":"ADDRESSES","rationale":"There is a proposed relationship, pending human evidence review",
        }]
        with self.assertRaisesRegex(ValueError,"target does not belong"):
            manifest_to_packet(config,self.checkout,
                               project_state=self.db.project_state(self.owner,self.project),
                               project_id=self.project)
        with self.assertRaisesRegex(ValueError,"existing project state"):
            manifest_to_packet(config,self.checkout)
        config["problem_links"][0]["relation"]="CAUSES"
        with self.assertRaisesRegex(ValueError,"relation not allowed"):
            manifest_to_packet(config,self.checkout,
                               project_state=self.db.project_state(self.owner,self.project),
                               project_id=self.project)

    def test_local_changes_are_not_source_authority(self):
        previous = self._packet()
        path = self.checkout / "project-one" / "README.md"
        path.write_text("Malicious uncommitted removal of source excerpt")
        self.assertEqual(previous, self._packet())

    def test_missing_source_or_wrong_origin_or_reversed_revision_fails(self):
        config = copy.deepcopy(self.config)
        config["repositories"][0]["evidence"][0]["needle"] = "Invented capability marker"
        with self.assertRaisesRegex(ValueError, "excerpt absent"):
            manifest_to_packet(config, self.checkout)
        config = copy.deepcopy(self.config)
        config["repositories"][0]["base"], config["repositories"][0]["head"] = (
            config["repositories"][0]["head"], config["repositories"][0]["base"]
        )
        with self.assertRaises(ValueError):
            manifest_to_packet(config, self.checkout)
        repo = self.checkout / "project-one"
        git(repo, "remote", "set-url", "origin", "https://github.com/other/project-one.git")
        with self.assertRaisesRegex(ValueError, "origin"):
            self._packet()

    def test_unsafe_paths_and_too_many_untrusted_commits_fail(self):
        config = copy.deepcopy(self.config)
        config["repositories"][0]["evidence"][0]["path"] = "../.env"
        with self.assertRaisesRegex(ValueError, "path"):
            manifest_to_packet(config, self.checkout)
        config = copy.deepcopy(self.config)
        config["repositories"][0]["evidence"][0]["path"] = "secrets.json"
        with self.assertRaisesRegex(ValueError, "path"):
            manifest_to_packet(config, self.checkout)

    def test_second_pinned_snapshot_adds_history_without_rewriting_old_evidence(self):
        original=self._packet()
        self.db.enqueue(self.owner,self.project,original,0,
                        self.db.preview(self.owner,self.project,original)["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")
        old_state=self.db.project_state(self.owner,self.project)
        repo=self.checkout / "project-one"
        (repo/"README.md").write_text("# Research\\nproject-one records its evidence authority and provenance\\nUpdated README at new revision\\n")
        git(repo,"add","README.md")
        self._commit(repo,"update documented scope")
        config=copy.deepcopy(self.config)
        config["repositories"][0]["base"]=config["repositories"][0]["head"]
        config["repositories"][0]["head"]=git(repo,"rev-parse","HEAD")
        updated=manifest_to_packet(config,self.checkout)
        review=self.db.preview(self.owner,self.project,updated)
        self.assertEqual(review["projected_new_records"]["semantic_clusters"],0)
        self.assertEqual(review["projected_new_records"]["semantic_nodes"],2)
        # Updated capability also gets a new candidate shared-topic link.
        self.assertEqual(review["projected_new_records"]["semantic_edges"],3)
        self.db.enqueue(self.owner,self.project,updated,review["project_revision"],review["packet_digest"])
        self.assertEqual(self.db.run_one_job()["status"],"succeeded")
        now=self.db.project_state(self.owner,self.project)
        self.assertEqual(len(now["semantic_nodes"]),8)
        self.assertEqual(len([n for n in now["semantic_nodes"].values()
                              if n["kind"]=="repository"]),2)
        self.assertTrue(set(old_state["semantic_nodes"]).issubset(now["semantic_nodes"]))
        self.assertEqual(len(now["semantic_packets"]),2)

    def test_private_authenticated_preview_queue_and_idempotent_replay(self):
        args = [
            "--db", str(self.dbfile), "--project", self.project,
            "--repo-root", str(self.checkout), "--manifest", str(self.manifest),
        ]
        before = self.db.project_state(self.owner, self.project)
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": self.token}):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args + ["preview"]), 0)
            preview = json.loads(out.getvalue())
            self.assertEqual(preview["review"]["projected_new_records"]["semantic_nodes"], 6)
            self.assertEqual(self.db.project_state(self.owner, self.project), before)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(args + [
                    "enqueue", "--expected-revision",
                    str(preview["review"]["project_revision"]),
                    "--expected-packet-digest",
                    preview["review"]["packet_digest"],
                ]), 0)
            job = json.loads(out.getvalue())["job_id"]
            self.assertEqual(self.db.run_one_job()["status"], "succeeded")
            self.assertEqual(self.db.get_job(self.owner, job)["status"], "succeeded")
            self.assertTrue(self.db.preview(self.owner, self.project, self._packet())["already_imported"])
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args + [
                    "enqueue", "--expected-revision", "0",
                    "--expected-packet-digest", preview["review"]["packet_digest"],
                ]), 2)
        atlas = self.db.project_projection(self.owner, self.project)["atlas"]
        self.assertEqual(atlas["summary"]["cluster_count"], 2)
        self.assertEqual(atlas["layers"], ["practical", "academic", "program"])
        self.assertTrue(all(item["layer_counts"]["practical"] == 0 for item in atlas["clusters"]))
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": self.viewer_token}):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args + ["preview"]), 2)
        with patch.dict(os.environ, {"CITE_REFINERY_TOKEN": "not-authorized"}):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(args + ["preview"]), 2)


if __name__ == "__main__":
    unittest.main()
