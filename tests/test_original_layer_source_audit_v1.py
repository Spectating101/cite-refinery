"""No-network, independently falsifiable public-source identity audit tests."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import unittest

from cite_refinery.original_layer_source_audit import (
    academic_source_audit, implementation_source_audit, FetchError, _repo_api_snapshot,
    SCHEMA, CROSSREF, GITHUB
)


class OriginalEvidenceTests(unittest.TestCase):
    def test_crossref_identity_confirms_only_bibliographic_record(self):
        manifest={
            "schema":"cite_refinery.open_corpus_manifest.v1",
            "source_records":[{
                "id":"EPMC-000","source_record":"10.1000/Research.2026",
                "url":"https://doi.org/10.1000/Research.2026",
                "origin_type":"scholarly_abstract_lead",
                "sha256":"a"*64,
                "title":"A measured comparison of hypothetical field methods","year":None
            },{
                "id":"WEB-001","source_record":"https://example.org",
                "url":"https://example.org","origin_type":"official_webpage_excerpt_unverified",
                "title":"Institutional service","sha256":"b"*64
            }]
        }
        def success(url):
            self.assertTrue(url.startswith(CROSSREF))
            return {"message":{"DOI":"10.1000/research.2026",
                    "title":["A measured comparison of hypothetical field methods"],
                    "published":{"date-parts":[[2026,6,12]]},
                    "type":"journal-article"}}
        r=academic_source_audit(manifest,fetcher=success)
        self.assertEqual(r["original_scholarly_leads_total"],1)
        self.assertEqual(r["doi_confirmed"],1)
        self.assertEqual(r["publication_year_added_from_crossref"],1)
        self.assertEqual(r["peer_review_or_method_findings_confirmed"],0)
        self.assertTrue(r["records"][0]["publisher_metadata_checked"])
        self.assertFalse(r["records"][0]["original_paper_fulltext_checked"])
        self.assertFalse(r["records"][0]["claims_or_methods_verified"])
        self.assertEqual(r["records"][0]["crossref_publication_year"],2026)

    def test_crossref_failed_identity_is_not_promoted_or_replaced(self):
        row={"id":"X1","source_record":"10.1000/abc","url":"https://doi.org/10.1000/abc",
             "origin_type":"scholarly_abstract_lead","sha256":"a"*64,
             "title":"Expected title","year":None}
        manifest={"schema":"cite_refinery.open_corpus_manifest.v1","source_records":[row]}
        def mismatched(url):
            return {"message":{"DOI":"10.1000/DIFFERENT",
                               "title":["Different paper"]}}
        result=academic_source_audit(manifest,fetcher=mismatched)
        self.assertEqual(result["doi_confirmed"],0)
        self.assertEqual(result["records"][0]["check_issue"],"doi_identity_mismatch")
        def error(url):
            raise FetchError("http_404")
        result=academic_source_audit(manifest,fetcher=error)
        self.assertEqual(result["records"][0]["metadata_status"],"not_confirmed")
        self.assertEqual(result["records"][0]["check_issue"],"http_404")

    def test_repository_exact_source_commit_and_root_scope(self):
        backlog={"schema":"cite_refinery.standalone_metadata_review_backlog.v1",
                 "sampled_pairs":3,
                 "entries":[
                    {"repository_id":"github:owner/project-a","category":"engineering",
                     "original_repository_url":"https://github.com/owner/project-a",
                     "original_semantic_label":"not_reviewed","review_complete":False,
                     "publisher_description":"A"},
                    {"repository_id":"github:owner/project-b","category":"education",
                     "original_repository_url":"https://github.com/owner/project-b",
                     "original_semantic_label":"not_reviewed","review_complete":False,
                     "publisher_description":"B"},
                    {"repository_id":"github:owner/project-a","category":"education",
                     "original_repository_url":"https://github.com/owner/project-a",
                     "original_semantic_label":"not_reviewed","review_complete":False,
                     "publisher_description":"A"},
                 ]}
        calls=[]
        def fake(url,token=None):
            calls.append(url)
            if "/contents?ref=" in url:
                return [{"name":"README.md"},{"name":"tests"},{"name":"LICENSE"},{"name":".github"}]
            if "/commits/" in url:
                return {"sha":"a"*40}
            if url.startswith(GITHUB):
                slug=url[len(GITHUB):]
                return {"full_name":slug,"default_branch":"main",
                        "html_url":"https://github.com/"+slug,
                        "license":{"spdx_id":"MIT"},"archived":False}
            raise AssertionError("Unexpected endpoint")
        result=implementation_source_audit(backlog,fetcher=fake,max_pairs=3)
        self.assertEqual(result["distinct_repositories_queried"],2)
        self.assertEqual(len(calls),6)
        self.assertEqual(result["original_repo_revision_and_root_checked_pairs"],3)
        self.assertEqual(result["distinct_source_categories_sampled"],2)
        self.assertEqual(result["root_test_dir_visible_pairs"],3)
        self.assertEqual(result["original_functions_independently_executed"],0)
        self.assertTrue(all(not x["independent_capability_demonstrated"] for x in result["records"]))
        self.assertEqual(result["records"][0]["original_source_snapshot"]["source_commit"],"a"*40)

    def test_ratelimit_or_stale_repo_cannot_look_like_success(self):
        record=_repo_api_snapshot("org/missing",
            fetcher=lambda url,token=None: (_ for _ in ()).throw(FetchError("http_403")))
        self.assertEqual(record["status"],"unavailable_or_inconclusive")
        self.assertIsNone(record["source_commit"])
        self.assertFalse(record["functional_quality_or_adoption_verified"])

    def test_invalid_original_backlog_rejected(self):
        a={"schema":"cite_refinery.standalone_metadata_review_backlog.v1",
           "sampled_pairs":1,
           "entries":[{"repository_id":"github:ok/repo","category":"flood",
                       "original_repository_url":"https://example.com/FAKE",
                       "original_semantic_label":"not_reviewed",
                       "review_complete":False,
                       "publisher_description":"A"}]}
        with self.assertRaisesRegex(ValueError,"identity"):
            implementation_source_audit(a,fetcher=lambda url,token=None:None)
        a["entries"][0]["original_repository_url"]="https://github.com/ok/repo"
        a["entries"][0]["review_complete"]=True
        with self.assertRaisesRegex(ValueError,"pre-approved"):
            implementation_source_audit(a,fetcher=lambda url,token=None:None)

    def test_invalid_source_manifest_type_fails(self):
        with self.assertRaises(ValueError):
            academic_source_audit({"schema":"other","source_records":[]})
        with self.assertRaises(ValueError):
            implementation_source_audit({"schema":"other","entries":[]})


if __name__=="__main__":
    unittest.main()
