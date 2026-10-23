"""Frozen 1,287-source Science overlap benchmark: non-promotion invariants."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from urllib.error import HTTPError
from tempfile import TemporaryDirectory
import json

from cite_refinery.science_reuse_census import (
    frozen_repositories, preregister_cohort, run_census, _digest, SCHEMA,
)

BASE = Path(__file__).resolve().parents[1] / "research_materials/opportunity_atlas"


def originals():
    p=json.loads((BASE/"github_repository_survey.json").read_text("utf-8"))
    f=json.loads((BASE/"github_frontier_repository_survey.json").read_text("utf-8"))
    return p, f


class ScienceReuseCensusTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary, cls.frontier=originals()

    def test_reconstructs_real_full_census_and_all_frozen_strata(self):
        rows=frozen_repositories(self.primary,self.frontier)
        self.assertEqual(len(rows),1287)
        self.assertEqual(len({r["url"].lower() for r in rows}),1287)
        self.assertTrue(all(r["url"]=="https://github.com/"+r["name"] for r in rows))
        self.assertEqual(len({c for r in rows for c in r["categories"]}),44)

    def test_sample_covers_categories_and_is_deterministic(self):
        rows=frozen_repositories(self.primary,self.frontier)
        sample=preregister_cohort(rows,count=100)
        self.assertEqual(len(sample),100)
        self.assertEqual(len({c for r in sample for c in r["categories"]}),44)
        self.assertEqual(sample,preregister_cohort(rows,count=100))
        self.assertNotEqual(_digest(sample), _digest(preregister_cohort(rows,count=101)))
        self.assertEqual(len(preregister_cohort(rows,count=1287)),1287)

    def test_original_repositories_reject_source_identity_drift(self):
        a=deepcopy(self.primary)
        a["repositories"][0]["url"]="http://localhost/secret"
        with self.assertRaisesRegex(ValueError,"Original source identity"):
            frozen_repositories(a,self.frontier)
        b=deepcopy(self.primary)
        b["collection_errors"]=["source failure"]
        with self.assertRaisesRegex(ValueError,"original clean"):
            frozen_repositories(b,self.frontier)

    def test_mixed_project_alias_missing_ambiguous_and_corrupt_do_not_promote(self):
        calls=[]
        def batch(urls):
            calls.append(urls)
            output=[]
            for i,url in enumerate(urls):
                match = ([{"source":"repository_alias", "project":{"id":31}}] if i%4==0
                         else ([{"source":"repository_url","project":{"id":11}},
                                {"source":"repository_alias","project":{"id":12}}] if i%4==1
                         else ([] if i%4==2 else [{"source":"broken"}])))
                output.append({"input_url":url,"matches":match})
            return output
        report=run_census(self.primary,self.frontier,max_repos=100,fetch_batch=batch)
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["cohort_size"],100)
        self.assertEqual(report["covered_original_strata"],44)
        self.assertEqual(len(calls),4)
        self.assertTrue(all(len(call)<=25 for call in calls))
        self.assertEqual(report["exact_single_project_matches"],28)
        self.assertEqual(report["ambiguous_multiple_project_matches"],24)
        self.assertEqual(report["reported_no_matching_project"],24)
        self.assertEqual(report["unaccounted_response_rows"],24)
        self.assertEqual(report["identity_responses_accounted_for"],100)
        self.assertEqual(report["status"],"partial_provider_or_response_failure")
        self.assertEqual(report["accepted_scientific_or_implementation_relations"],0)
        self.assertTrue(report["not_source_functionality_verified"])
        self.assertTrue(report["not_independent_relevance_or_accuracy_benchmark"])

    def test_partial_provider_batch_does_not_count_failure_as_no_match(self):
        called=0
        def batch(urls):
            nonlocal called
            called+=1
            if called == 1:
                raise OSError("source temporarily unavailable")
            return [{"input_url":url,"matches":[]} for url in urls]
        report=run_census(self.primary,self.frontier,max_repos=100,fetch_batch=batch,workers=1)
        self.assertEqual(report["not_evaluated_due_to_provider_failure"],25)
        self.assertEqual(report["reported_no_matching_project"],75)
        self.assertEqual(report["exact_single_project_matches"],0)
        self.assertEqual(report["status"],"partial_provider_or_response_failure")
        self.assertEqual(len(report["failed_batches"]),1)

    def test_successful_full_100_valid_page_is_identity_only(self):
        def batch(urls):
            return [{"input_url":u,"matches":[{"project":{"id":i+1},
                                              "source":"url_exact"}]}
                    for i,u in enumerate(urls)]
        report=run_census(self.primary,self.frontier,max_repos=100,fetch_batch=batch)
        self.assertEqual(report["status"],
                         "complete_metadata_identity_census_no_semantic_quality_claim")
        self.assertEqual(report["exact_single_project_matches"],100)
        self.assertEqual(report["reported_no_matching_project"],0)
        self.assertFalse(report["underconversion_or_customer_adoption_verified"])

    def test_omitted_or_extra_provider_ids_rejected_or_unaccounted(self):
        def omission(urls):
            return [{"input_url":u,"matches":[]} for u in urls[:-1]]
        r=run_census(self.primary,self.frontier,max_repos=100,fetch_batch=omission)
        self.assertEqual(r["unaccounted_response_rows"],4)
        self.assertEqual(r["reported_no_matching_project"],96)
        def rogue(urls):
            return [{"input_url":"https://github.com/rogue/outside","matches":[]}]
        with self.assertRaisesRegex(ValueError,"Source mismatch"):
            run_census(self.primary,self.frontier,max_repos=100,fetch_batch=rogue)

    def test_bad_source_count_or_unfrozen_sampling_rejected(self):
        repo=frozen_repositories(self.primary,self.frontier)
        for n in (20,43,1288):
            with self.assertRaises(ValueError):
                preregister_cohort(repo,count=n)
        altered=deepcopy(self.primary)
        altered["repositories"].pop(0)
        # If source also happens to be duplicated in frontier, we cannot
        # claim inventory changed just by removing this one occurrence.
        with self.assertRaises(ValueError):
            frozen_repositories({"schema":"wrong","collection_errors":[],
                                 "repositories":[]} , self.frontier)

    def test_refuses_malicious_string_values_before_fetching(self):
        a=deepcopy(self.primary)
        a["repositories"][0]["full_name"]="alice/../../secret"
        with self.assertRaisesRegex(ValueError,"Original source identity"):
            frozen_repositories(a,self.frontier)
        with self.assertRaisesRegex(ValueError,"bounded"):
            run_census(self.primary,self.frontier,max_repos=100,fetch_batch=lambda _:[],workers=7)


if __name__ == "__main__":
    import unittest
    unittest.main()
