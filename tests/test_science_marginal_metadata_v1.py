"""Marginal Science metadata benchmark; genuine source census and mock context."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import os
import unittest

from cite_refinery.science_marginal_metadata import (
    validate_sample, benchmark, SCHEMA, SAMPLE,
)

ROOT=Path(__file__).resolve().parents[1]
SURVEY=ROOT/"research_materials/opportunity_atlas"
SAMPLE_PATH=ROOT/"research_materials/external_landscape/science_marginal_context_sample_v1.json"


class MarginalMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample=json.loads(SAMPLE_PATH.read_text("utf-8"))
        cls.primary=json.loads((SURVEY/"github_repository_survey.json").read_text("utf-8"))
        cls.frontier=json.loads((SURVEY/"github_frontier_repository_survey.json").read_text("utf-8"))
        path=os.getenv("SCIENCE_FULL_CENSUS_PATH")
        if not path:
            raise unittest.SkipTest("Requires true original 1287-repository census artifact, not invented fixture")
        cls.census=json.loads(Path(path).read_text("utf-8"))

    def mock_context(self, project_id):
        return {"project_id":project_id,"repository_url":None,
                "descriptions":[{"text":"publisher supplied"}],
                "languages":[{"language":"Python"}],
                "packages":[{"purl":"pkg:pypi/example"}],
                "direct_dependencies":[{"purl":"pkg:pypi/dep"}],
                "dependencies_indexed_at":"2026-10-21T00:00:00Z"}

    def test_original_source_fixture_derived_from_complete_archived_census(self):
        matched,missing,sources=validate_sample(
            self.sample,self.census,self.primary,self.frontier)
        self.assertEqual((len(matched),len(missing)),(20,20))
        self.assertEqual(len({x["repository"] for x in matched}),20)
        self.assertEqual(len(set(missing)),20)
        self.assertEqual(set(x["repository"] for x in matched)&set(missing),set())
        self.assertTrue(all(url.casefold() in sources for url in missing))

    def test_mock_source_metadata_counts_not_capability(self):
        report=benchmark(self.sample,self.census,self.primary,self.frontier,
                         fetch=self.mock_context)
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["science_context_read_successes"],20)
        self.assertEqual(report["science_with_package_metadata"],20)
        self.assertEqual(report["science_with_indexed_direct_dependencies"],20)
        self.assertEqual(report["science_with_multiple_descriptions"],0)
        self.assertEqual(report["status"],"complete_catalogue_metadata_utility_only")
        self.assertEqual(report["accepted_graph_evidence_edges"],0)
        self.assertFalse(report["independent_software_quality_improvement_verified"])
        self.assertFalse(report["independent_analyst_time_savings_measured"])
        self.assertTrue(all(not x["original_code_execution_verified"] for x in report["inspection"]))

    def test_absent_science_indexing_timestamp_never_claims_indexed_dependencies(self):
        def stale(project_id):
            d=self.mock_context(project_id)
            d["dependencies_indexed_at"]=None
            return d
        report=benchmark(self.sample,self.census,self.primary,self.frontier,fetch=stale)
        self.assertEqual(report["science_with_indexed_direct_dependencies"],0)
        self.assertEqual(report["science_with_package_metadata"],20)

    def test_provider_errors_are_reported_as_unknown_not_no_catalogue(self):
        def unavailable(project_id):
            if project_id%2:
                raise OSError("network unavailable")
            return self.mock_context(project_id)
        result=benchmark(self.sample,self.census,self.primary,self.frontier,fetch=unavailable)
        self.assertEqual(result["status"],"partial_catalogue_metadata_utility_provider_failure")
        self.assertTrue(result["science_context_errors"])
        self.assertEqual(result["science_context_read_successes"]+
                         len(result["science_context_errors"]),20)

    def test_wrong_project_identity_is_not_accepted(self):
        def wrong(project_id):
            d=self.mock_context(project_id)
            d["project_id"]=project_id+1
            return d
        result=benchmark(self.sample,self.census,self.primary,self.frontier,fetch=wrong)
        self.assertEqual(result["science_context_read_successes"],0)
        self.assertEqual(len(result["science_context_errors"]),20)
        self.assertEqual(result["accepted_graph_evidence_edges"],0)

    def test_sample_tampering_or_census_reclassification_fails_closed(self):
        fixture=deepcopy(self.sample)
        fixture["matched"][0]["science_project_id"]=7
        with self.assertRaisesRegex(ValueError,"preregistered"):
            validate_sample(fixture,self.census,self.primary,self.frontier)
        fixture=deepcopy(self.sample)
        fixture["unmatched"][0]="https://github.com/new/unapproved"
        with self.assertRaisesRegex(ValueError,"preregistered"):
            validate_sample(fixture,self.census,self.primary,self.frontier)
        fake=deepcopy(self.census)
        fake["exact_single_project_matches"]=999
        with self.assertRaisesRegex(ValueError,"Expected original complete"):
            validate_sample(self.sample,fake,self.primary,self.frontier)
        fake=deepcopy(self.census)
        fake["survey_fingerprint_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"source census"):
            validate_sample(self.sample,fake,self.primary,self.frontier)

    def test_malformed_parallelism_rejected(self):
        with self.assertRaisesRegex(ValueError,"limited"):
            benchmark(self.sample,self.census,self.primary,self.frontier,
                      fetch=self.mock_context,workers=10)


if __name__=="__main__":
    unittest.main()
