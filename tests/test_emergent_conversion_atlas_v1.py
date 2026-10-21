"""Open-ended conversion discovery and optional funding sidecar; no fake quality."""
from __future__ import annotations
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
import unittest

from cite_refinery.open_corpus_atlas import (
    CONVERSION_SCHEMA, DISCOVERY_SCHEMA, FUNDING_SCHEMA,
    prepare_conversion_universe,emergent_conversion_prompt,
    validate_emergent_conversion,funding_overlay,render_conversion_discovery,
    attach_original_repository_metadata,screen_emergent_batch
)
from cite_refinery.layered_cli import main as cli

ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads((ROOT/path).read_text())

class ConversionAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas=load('research_materials/runtime_trials/open_corpus_20261020/global_atlas.json')
        cls.manifest=load('research_materials/runtime_trials/open_corpus_20261020/source_manifest.json')
        cls.survey=load('research_materials/opportunity_atlas/github_frontier_repository_survey.json')
        cls.catalog=load('research_materials/opportunity_atlas/funding_enablers_small_catalog_20261021.json')
        cls.universe=prepare_conversion_universe(cls.atlas,cls.survey,cls.manifest)

    def fake_model(self):
        repos=self.universe["selected_repositories"]
        domains=self.universe["emergent_domains"]
        return {
            "schema":DISCOVERY_SCHEMA,
            "hypotheses":[
                {"id":"CV-01","mode":"asset_to_problem",
                 "asset_ids":[repos[0]["id"]],
                 "domain_labels":[domains[0]["label"]],
                 "source_ids":[domains[0]["source_ids"][0]],
                 "connection":"Test a source-reported capability in an otherwise unrelated practical workflow.",
                 "why_nonobvious":"An implementation mechanism from one search macro may transfer to another sector with different vocabulary.",
                 "potential_quality_signal":"The source listing reports an active repository and a claimed feature, but code quality is not yet tested.",
                 "conversion_barrier":"missing_evidence",
                 "barrier_explanation":"No independent repository test or user study demonstrates whether this particular recombination is useful.",
                 "recombination_or_use":"Clone the permitted repository and test one clearly scoped interface against independent field requirements.",
                 "value_forms":["technical_capability","internal_portfolio"],
                 "first_falsification":"Run an original-source test on realistic input and reject the connection if prerequisites differ.",
                 "observed_conversion_status":"unknown_not_measured",
                 "technical_quality_status":"not_independently_tested",
                 "relationship_status":"candidate_not_verified"},
                {"id":"CV-02","mode":"asset_to_asset",
                 "asset_ids":[repos[1]["id"],repos[2]["id"]],
                 "domain_labels":[],"source_ids":[],
                 "connection":"Investigate whether two independently sourced implementation capabilities can combine at a technical interface.",
                 "why_nonobvious":"Their unrelated GitHub search categories would not ordinarily lead to a common development task.",
                 "potential_quality_signal":"Both components have maintainer descriptions but neither has a reproducible original integration validation.",
                 "conversion_barrier":"integration",
                 "barrier_explanation":"An interface and license mismatch may make the new combination impractical despite individual utility.",
                 "recombination_or_use":"Build a minimal isolated adapter only after inspecting dependency and license obligations.",
                 "value_forms":["technical_capability","research_knowledge"],
                 "first_falsification":"Use documented public API contracts to determine whether compatible data types can be exchanged.",
                 "observed_conversion_status":"unknown_not_measured",
                 "technical_quality_status":"not_independently_tested",
                 "relationship_status":"candidate_not_verified"},
            ],
            "unmatched_note":"Other domains remain unsampled at the repository level; absence of a match in this short run is not global absence."
        }

    def test_wide_universe_is_not_narrowed_to_market_or_only_practical_roots(self):
        u=self.universe
        self.assertEqual(u["survey_repositories_total"],605)
        self.assertEqual(u["source_corpus_total"],63)
        self.assertEqual(len(u["emergent_domains"]),8)
        self.assertGreaterEqual(len(u["selected_repositories"]),30)
        self.assertGreaterEqual(len({r["macro"] for r in u["selected_repositories"]}),5)
        self.assertTrue(all(r["technical_quality_independently_verified"] is False
                            and r["underconversion_confirmed"] is False
                            for r in u["selected_repositories"]))
        self.assertIn("No target sector",emergent_conversion_prompt(u))
        later=prepare_conversion_universe(self.atlas,self.survey,self.manifest,offset=1)
        self.assertNotEqual(set(r["id"] for r in later["selected_repositories"]),
                            set(r["id"] for r in u["selected_repositories"]))

    def test_asymmetry_is_a_hypothesis_not_a_forced_three_layer_chain(self):
        record=validate_emergent_conversion(self.fake_model(),self.universe)
        self.assertEqual(record["schema"],CONVERSION_SCHEMA)
        self.assertEqual(record["candidate_connection_count"],2)
        self.assertEqual(record["candidate_connections"][1]["mode"],"asset_to_asset")
        self.assertEqual(record["candidate_connections"][1]["source_evidence"],[])
        self.assertEqual(len(record["candidate_connections"][0]["source_evidence"]),1)
        self.assertTrue(all(not x["confirmed_adoption_or_impact"] and
                            not x["accepted_graph_relationship"] for x in record["candidate_connections"]))
        self.assertEqual(record["verified_underconverted_assets"],0)
        self.assertEqual(record["verified_genuinely_high_quality_assets"],0)
        self.assertEqual(record["new_graph_edges_accepted"],0)
        self.assertFalse(record["monetization_required"])
        self.assertIn("Potential non-obvious connections",render_conversion_discovery(record))

    def test_batch_salvages_valid_cross_domain_discovery_but_fails_closed_on_fake_repo(self):
        raw=self.fake_model()
        raw["hypotheses"][1]["asset_ids"][1]="github:imaginary/does-not-exist"
        out=screen_emergent_batch(raw,self.universe)
        self.assertEqual(out["candidate_connection_count"],1)
        self.assertEqual(out["submitted_candidate_count"],2)
        self.assertEqual(out["rejected_candidate_count"],1)
        reject=out["rejected_model_candidates"][0]
        self.assertIn("Unrecognized asset",reject["reason"])
        self.assertEqual(len(reject["candidate_payload_sha256"]),64)
        self.assertEqual(out["new_graph_edges_accepted"],0)

    def test_zero_discoveries_is_valid_not_auto_generated_nonsense(self):
        empty={"schema":DISCOVERY_SCHEMA,"hypotheses":[],
               "unmatched_note":"No mechanism-backed relationship could be defended from this limited cross-industry source sample."}
        j=validate_emergent_conversion(empty,self.universe)
        self.assertEqual(j["candidate_connection_count"],0)
        self.assertIn("No relationships met",render_conversion_discovery(j))

    def test_two_assets_may_jointly_address_one_domain_without_forcing_extra_layer(self):
        p=self.fake_model()
        p["hypotheses"][0]["asset_ids"].append(self.universe["selected_repositories"][1]["id"])
        r=validate_emergent_conversion(p,self.universe)
        self.assertEqual(len(r["candidate_connections"][0]["asset_ids"]),2)
        self.assertFalse(r["candidate_connections"][0]["accepted_graph_relationship"])

    def test_source_integrity_domain_scope_and_invalid_quality_promotion(self):
        mutations=[
            lambda a:a["hypotheses"][0]["asset_ids"].__setitem__(0,"github:FAKE/ABSENT"),
            lambda a:a["hypotheses"][0]["source_ids"].__setitem__(0,"EPMC-DOES-NOT-EXIST"),
            lambda a:a["hypotheses"][0].update(technical_quality_status="verified_excellent"),
            lambda a:a["hypotheses"][0].update(observed_conversion_status="market_disproved"),
            lambda a:a["hypotheses"][0].update(relationship_status="qualified"),
            lambda a:a["hypotheses"][0].update(financial_return_twd=50000),
            lambda a:a["hypotheses"][0].update(conversion_barrier="confirmed_marketing_failure"),
            lambda a:a["hypotheses"][0].update(value_forms=["cash_profit_guaranteed"]),
            lambda a:a["hypotheses"][0].update(id="CV-02"),
            lambda a:a["hypotheses"][1].update(domain_labels=[self.universe["emergent_domains"][0]["label"]]),
        ]
        for fn in mutations:
            j=deepcopy(self.fake_model())
            fn(j)
            with self.assertRaises(ValueError):
                validate_emergent_conversion(j,self.universe)

    def test_reference_provenance_is_bounded_to_source_manifest(self):
        model=self.fake_model()
        result=validate_emergent_conversion(model,self.universe)
        first=result["candidate_connections"][0]["source_evidence"][0]
        self.assertEqual(first["url"],self.universe["source_manifest"][first["id"]]["url"])
        self.assertEqual(first["sha256"],self.universe["source_manifest"][first["id"]]["sha256"])
        modified=deepcopy(self.manifest)
        modified["source_records"][0]["id"]="FORGED-NEW-SOURCE"
        with self.assertRaisesRegex(ValueError,"source manifest"):
            prepare_conversion_universe(self.atlas,self.survey,modified)

    def test_observed_repo_metadata_is_not_falsely_upgraded_to_high_quality(self):
        j=validate_emergent_conversion(self.fake_model(),self.universe)
        refs=[x.split(":",1)[1] for r in j["candidate_connections"][0:2]
              for x in r["asset_ids"]]
        fake=[]
        for name in refs:
            fake.append({
                "repository":name,"url":"https://github.com/"+name,
                "repository_exists":True,"api_snapshot_at_utc":"2026-10-21T00:00:00Z",
                "archived":False,"license_api_label":"MIT",
                "root_test_directory_detected_not_executed":True,
                "github_configuration_directory_present":True,
                "independent_quality_qualified":False,
                "actual_adoption_verified":False,"original_code_executed":False,
                "conversion_failure_reason_verified":False})
        audit={"schema":"cite_refinery.public_candidate_repo_audit.v1",
               "independently_quality_verified":0,
               "actual_underconversion_verified":0,"repositories":fake}
        upgraded=attach_original_repository_metadata(j,audit)
        self.assertEqual(upgraded["original_repository_metadata_audit"]["checked_repo_count"],3)
        self.assertEqual(upgraded["original_repository_metadata_audit"]["repo_tests_executed"],0)
        self.assertEqual(upgraded["verified_genuinely_high_quality_assets"],0)
        bad=deepcopy(audit)
        bad["repositories"][0]["original_code_executed"]=True
        with self.assertRaisesRegex(ValueError,"executable quality"):
            attach_original_repository_metadata(j,bad)

    def test_funding_is_a_small_separate_eligibility_unknown_overlay(self):
        f=funding_overlay(self.catalog)
        self.assertEqual(len(f["channels"]),6)
        self.assertFalse(f["is_foundational_fourth_layer"])
        self.assertEqual(f["eligible_opportunities_verified"],0)
        self.assertEqual(f["funded_relationships"],0)
        self.assertTrue(all(not x["applicant_eligibility_confirmed"]
                            and not x["funding_award_or_commitment"]
                            for x in f["channels"]))
        csg=next(x for x in f["channels"] if x["id"]=="csg_unresolved")
        self.assertIsNone(csg["source_url"])
        self.assertEqual(csg["type"],"unresolved_source")
        self.assertIn("NLnet",render_conversion_discovery(
            validate_emergent_conversion(self.fake_model(),self.universe),f))
        invalid=deepcopy(self.catalog)
        invalid["channels"][0]["source_url"]="http://localhost/admin"
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            funding_overlay(invalid)
        invalid=deepcopy(self.catalog)
        invalid["channels"][0]["applicant_eligibility_confirmed"]=True
        with self.assertRaises(ValueError):
            funding_overlay(invalid)

    def test_cli_replays_model_without_provider_or_workspace_side_effect(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            saved=root/"model.json"
            saved.write_text(json.dumps(self.fake_model()))
            args=["investigate","--workspace",str(root/"should_not_create"),
                  "discover-conversions",
                  "--atlas",str(ROOT/"research_materials/runtime_trials/open_corpus_20261020/global_atlas.json"),
                  "--manifest",str(ROOT/"research_materials/runtime_trials/open_corpus_20261020/source_manifest.json"),
                  "--repository-survey",str(ROOT/"research_materials/opportunity_atlas/github_frontier_repository_survey.json"),
                  "--funding-catalog",str(ROOT/"research_materials/opportunity_atlas/funding_enablers_small_catalog_20261021.json"),
                  "--model-output",str(saved),
                  "--json-out",str(root/"out.json"),
                  "--markdown-out",str(root/"out.md")]
            out=StringIO()
            with redirect_stdout(out):cli(args)
            response=json.loads(out.getvalue())
            self.assertEqual(response["new_candidate_connections"],2)
            self.assertEqual(response["quality_independently_verified"],0)
            self.assertEqual(response["funding_resources"],6)
            self.assertFalse((root/"should_not_create").exists())
            self.assertEqual(len(json.loads((root/"out.json").read_text())["candidate_connections"]),2)
            with self.assertRaisesRegex(ValueError,"overwrite"):
                cli(args)
            with (ROOT/"pyproject.toml").open("rb") as f:
                scripts=tomllib.load(f)["project"]["scripts"]
            self.assertEqual(len(scripts),50)
            self.assertNotIn("cite-refinery-discover-conversions",scripts)

if __name__=="__main__":
    unittest.main()
