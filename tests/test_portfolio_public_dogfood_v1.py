"""Test portfolio graph source integrity and no private/acceptance leakage.

These synthetic README fixtures are only interface tests; CI separately runs
against all eight real original public README blobs and actual model weights.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha1
import unittest

from cite_refinery.portfolio_public_dogfood import (
    ALLOWLIST, QUESTION_SET, NEGATIVE_QUESTIONS, validate_manifest,
    fetch_repo, build_packet, run_public_portfolio, _source_quote,
)


def sample():
    docs={}
    repos=[]
    for idx,name in enumerate(sorted(ALLOWLIST)):
        data=("# "+name+"\n\nSoftware that checks public evidence, manages "
              "source records and requires external validation before institutional release. "
              "This is a research demonstration, not a verified field outcome. "
              "Independent validation is pending; no commercial use is established.\n").encode()
        blob=sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
        head=("%040x"%(idx+1))
        repos.append({"repo":name,"head_sha":head,"readme_blob_sha":blob,
                      "operator_declared_category":"development_sample"})
        docs[name]={"sha":blob,"encoding":"base64",
                    "content":base64.b64encode(data).decode()}
    manifest={
        "schema":"cite_refinery.public_portfolio_dogfood_sources.v1",
        "owner":"Spectating101","public_only":True,
        "never_publish_private_files":True,
        "independent_gold_available":False,
        "repositories":repos,
        "private_repositories_excluded_by_allowlist":True,
    }
    return manifest,docs


def mocked(docs,*,fail_readme=False,fail_ci=False):
    def fetch(url,token=None):
        name=url.split("/repos/Spectating101/",1)[1].split("/",1)[0]
        if url.split("?")[0].endswith("README.md"):
            if fail_readme: return {**docs[name],"sha":"0"*40}
            return docs[name]
        if fail_ci: raise OSError("unavailable")
        return {"workflow_runs":[{
            "id":100,"name":"unit-only",
            "conclusion":"success","head_sha":"0"*40,
            "html_url":"https://github.com/Spectating101/"+name+"/actions/runs/100",
        }]}
    return fetch


class PortfolioPublicSourceDogfoodTests(unittest.TestCase):
    def setUp(self):
        self.manifest,self.docs=sample()

    def test_original_eight_public_source_scope(self):
        self.assertEqual(len(validate_manifest(self.manifest)),8)
        self.assertEqual(len(QUESTION_SET),8)
        self.assertEqual(len(NEGATIVE_QUESTIONS),3)
        bad=deepcopy(self.manifest)
        bad["repositories"][0]["repo"]="unlisted-private-project"
        with self.assertRaisesRegex(ValueError,"private"):
            validate_manifest(bad)
        bad=deepcopy(self.manifest)
        bad["public_only"]=False
        with self.assertRaisesRegex(ValueError,"bounded"):
            validate_manifest(bad)

    def test_pinned_original_source_bytes_are_verified(self):
        row=self.manifest["repositories"][0]
        obj=fetch_repo(row,fetch_json=mocked(self.docs))
        self.assertEqual(obj["readme_blob_sha"],row["readme_blob_sha"])
        self.assertIn(row["head_sha"],obj["pinned_source_url"])
        with self.assertRaisesRegex(ValueError,"nonpinned"):
            fetch_repo(row,fetch_json=mocked(self.docs,fail_readme=True))

    def test_actual_graph_workspace_never_accepts_claims(self):
        report=run_public_portfolio(self.manifest,fetch_json=mocked(self.docs))
        self.assertTrue(report["atlas_actual_semantic_graph_ingested"])
        self.assertTrue(report["atlas_actual_product_workspace_rendered"])
        self.assertEqual(len(report["source_snapshots"]),8)
        self.assertEqual(report["layers"]["program"],8)
        self.assertEqual(report["layers"]["academic"],1)
        self.assertEqual(report["layers"]["neutral"],8)
        self.assertEqual(report["layers"]["practical"],8)
        self.assertEqual(report["edges_by_status"]["candidate"],12)
        self.assertEqual(report["edges_by_status"]["qualified"],8)
        self.assertEqual(report["maintainer_claims_independently_verified"],0)
        self.assertEqual(report["accepted_cross_repo_compatibility"],0)
        self.assertFalse(report["autonomous_semantic_understanding_demonstrated"])
        self.assertEqual(report["private_repositories_included"],0)
        self.assertEqual(report["same_commit_ci_observed"],0)

    def test_missing_ci_is_unknown_never_false_repository_verdict(self):
        result=run_public_portfolio(self.manifest,fetch_json=mocked(self.docs,fail_ci=True))
        self.assertEqual(result["layers"].get("practical",0),0)
        self.assertEqual(result["same_commit_ci_observed"],0)
        self.assertEqual(result["source_edges"],12)
        self.assertEqual(set(result["edges_by_status"]),{"candidate"})
        self.assertEqual({x["status"] for x in result["ci_read_only_observations"].values()},
                         {"provider_unavailable"})
        self.assertEqual(result["accepted_cross_repo_compatibility"],0)

    def test_quoted_negative_stance_is_maintainer_statement_not_field_certification(self):
        quote=_source_quote("# Demo\n\nMachine checks are complete. There is no live product evaluation. It is not published.")
        self.assertIn("no live product",quote)
        report=run_public_portfolio(self.manifest,fetch_json=mocked(self.docs))
        self.assertTrue(all(e["status"] in {"candidate","qualified"}
                            for e in report["packet"]["edges"]))
        self.assertFalse(any(e["status"]=="asserted" for e in report["packet"]["edges"]))


if __name__=="__main__":
    unittest.main()
