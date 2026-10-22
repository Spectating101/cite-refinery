"""Academic source-grounded semantic chain: real-index staging, bounded mock model, no false scientific claims."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from cite_refinery.academic_evidence_atlas import build_academic_atlas
from cite_refinery.external_llm_runtime import LLMUnavailable
from cite_refinery.source_grounded_semantic_answer import (
    SCHEMA,run,verified_available_sources,_windows,main,_validate_map)

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"research_materials/runtime_trials/richer_corpus_20261020"

BODY1=("The observational classroom study included 1,019 pupils from 51 elementary schools "
       "in Coimbra, Portugal. Elevated carbon dioxide was associated with reported lack of "
       "concentration. This is an association, not evidence that installing CO2 monitors "
       "causally prevents asthma or improves respiratory health. "
       "The study did not measure the effectiveness of CO2 alarm installations.")
BODY2=("The battery recycling manuscript presents a techno-economic model rather than "
       "a series of confirmed commercial operations. The modeled profit range includes "
       "negative and positive results, with costs depending on transport and labor. "
       "The source does not show all battery recycling businesses make money in Taiwan.")


def verified_map_and_texts():
    a=build_academic_atlas(
        json.loads((FROZEN/"development_source_manifest.json").read_text()),
        json.loads((FROZEN/"frozen_split_receipt.json").read_text()))
    out=deepcopy(a)
    keys=sorted(out["sources"])[:2]
    texts={keys[0]:BODY1,keys[1]:BODY2}
    for sid,txt in texts.items():
        out["sources"][sid]["text_sha256"]=sha256(txt.encode()).hexdigest()
    # This synthetic local fixture does NOT represent actual original document
    # content for those two IDs. Only the runtime chain and attack handling
    # are tested here; never publish as independent scientific verification.
    return out,texts


def dummy(stage_overrides=None):
    if stage_overrides is None:stage_overrides={}
    def call(prompt,phase):
        return stage_overrides[phase] if phase in stage_overrides else {}
    return call


class SemanticVerticalSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas,cls.texts=verified_map_and_texts()
        cls.sid=sorted(cls.texts)[0]
        cls.sid2=sorted(cls.texts)[1]
        cls.quote="Elevated carbon dioxide was associated with reported lack of concentration."
        cls.question="Could sensors in poorly ventilated schools actually stop children getting asthma?"

    def base_stages(self):
        return {
            "rank_sources":{"candidates":[{"source_id":self.sid,
                "reason":"The study examines classroom air exposures and concentration."}],
                "abstain":False},
            "select_passages":{"passages":[{"source_id":self.sid,"passage_id":"P001",
                "reason":"Direct information about exposure and study design."}],
                "abstain":False},
            "interpret_answer":{"status":"supported",
                "answer":"The source reports an association with concentration, not a demonstrated reduction in asthma.",
                "claims":[{"source_id":self.sid,"passage_id":"P001",
                    "statement":"Elevated classroom CO2 was associated with lack of concentration in an observational survey.",
                    "quote":self.quote,"stance":"supports"}],
                "limitations":"Observational study, no monitor deployment or asthma intervention was tested."},
        }

    def execute(self,stages=None,critic=None,atlas=None,texts=None,mode="operator_supplied_model_responses_unverified"):
        return run(self.question,atlas or self.atlas,texts if texts is not None else self.texts,
                   dummy(stages if stages is not None else self.base_stages()),
                   mode=mode,provider_label="unit_test_simulated",
                   critic_call=(lambda prompt,phase:critic) if critic is not None else None,
                   critic_provider_label="mock_other_family" if critic else None)

    def test_complete_query_to_semantic_ranking_original_quote_chain(self):
        report=self.execute()
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["result"],"candidate_answer_review_only")
        self.assertEqual(len(report["claims"]),1)
        quote=report["claims"][0]
        self.assertEqual(quote["quote"],self.quote)
        self.assertEqual(quote["source_id"],self.sid)
        self.assertTrue(quote["verbatim_original_text_verified"])
        self.assertEqual(quote["source_quote_sha256"],
                         sha256(self.quote.encode("utf-8")).hexdigest())
        self.assertFalse(quote["semantic_entailment_independently_verified"])
        self.assertEqual(len(report["provenance"]["stage_receipts"]),3)
        self.assertFalse(report["provenance"]["independently_human_approved"])
        self.assertEqual(report["review_gate"],"NOT_APPROVED")
        self.assertEqual(report["provenance"]["model_execution_mode"],
                         "operator_supplied_model_responses_unverified")

    def test_original_source_sha_validation_and_hidden_holdout_guard(self):
        with TemporaryDirectory() as td:
            directory=Path(td)
            for sid,text in self.texts.items():
                (directory/(sid+".txt")).write_text(text,encoding="utf-8")
            self.assertEqual(verified_available_sources(self.atlas,directory),
                             self.texts)
            a=directory/(self.sid+".txt")
            a.write_text(BODY1+" tampered")
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                verified_available_sources(self.atlas,directory)
            a.write_text(BODY1)
            (directory/"HELDOUT-FAKE.txt").write_text(BODY1)
            with self.assertRaisesRegex(ValueError,"unknown/heldout"):
                verified_available_sources(self.atlas,directory)
            (directory/"HELDOUT-FAKE.txt").unlink()
        bad=deepcopy(self.atlas)
        bad["provenance"]["heldout_source_id_or_text_imported"]=True
        with self.assertRaisesRegex(ValueError,"heldout"):
            _validate_map(bad)

    def test_missing_local_extracted_source_text_abstains_without_model_calls(self):
        def unexpected(prompt,phase):
            raise AssertionError("Never call LLM without authenticated original passage")
        report=run(self.question,self.atlas,{},unexpected,
                   mode="authenticated_live_model",provider_label="agy")
        self.assertEqual(report["result"],"abstained")
        self.assertEqual(report["reason"],"no_available_original_extracted_text")
        self.assertEqual(report["claims"],[])

    def test_first_semantic_ranking_can_recover_paraphrased_topic(self):
        observed=[]
        stages=self.base_stages()
        def run_model(prompt,phase):
            observed.append((phase,prompt))
            return stages[phase]
        report=run("pupils lose focus when school air is stale",self.atlas,
                   self.texts,run_model,
                   mode="operator_supplied_model_responses_unverified",
                   provider_label="model_fixture")
        self.assertEqual(report["result"],"candidate_answer_review_only")
        self.assertEqual([x[0] for x in observed],
                         ["rank_sources","select_passages","interpret_answer"])
        self.assertIn("pupils lose focus when school air is stale",observed[0][1])
        self.assertIn(self.quote,observed[2][1])

    def test_model_invents_new_source_or_hallucinates_passage_rejected(self):
        cases=[
            ("rank_sources",{"candidates":[{"source_id":"HELDOUT-secret",
               "reason":"Different source not in the vetted material."}],
               "abstain":False},"invented"),
            ("select_passages",{"passages":[{"source_id":self.sid,
               "passage_id":"P999","reason":"No such original passage."}],
               "abstain":False},"invented"),
        ]
        for phase,payload,reason in cases:
            with self.subTest(phase=phase):
                stages=self.base_stages();stages[phase]=payload
                with self.assertRaisesRegex(ValueError,reason):
                    self.execute(stages)
        stages=self.base_stages()
        stages["interpret_answer"]["claims"][0]["quote"]="A randomized trial proved total elimination of asthma."
        with self.assertRaisesRegex(ValueError,"Fabricated quote"):
            self.execute(stages)

    def test_missing_citations_cannot_be_reported_as_supported(self):
        stages=self.base_stages()
        stages["interpret_answer"]["claims"]=[]
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            self.execute(stages)
        stages["interpret_answer"]["status"]="insufficient_evidence"
        stages["interpret_answer"]["answer"]="Not enough evidence in the supplied original passages."
        report=self.execute(stages)
        self.assertEqual(report["result"],"abstained")
        self.assertEqual(report["claims"],[])

    def test_model_abstains_from_retrieval_without_inventing_an_answer(self):
        stages=self.base_stages()
        stages["rank_sources"]={"candidates":[],"abstain":True}
        r=self.execute(stages)
        self.assertEqual(r["reason"],"model_abstained_from_source_selection")
        self.assertEqual(len(r["provenance"]["stage_receipts"]),1)
        stages=self.base_stages()
        stages["select_passages"]={"passages":[],"abstain":True}
        r=self.execute(stages)
        self.assertEqual(r["reason"],"model_abstained_from_passages")

    def test_critic_can_block_exactly_quoted_but_semantically_overstated_claim(self):
        critic={"assessment":"overreach","unsafe_claim_indices":[0],
                "reason":"The study reports association, not a randomized prevention experiment."}
        r=self.execute(critic=critic)
        self.assertEqual(r["result"],"abstained")
        self.assertEqual(len(r["claims"]),1)
        self.assertTrue(r["claims"][0]["verbatim_original_text_verified"])
        self.assertFalse(r["claims"][0]["semantic_entailment_independently_verified"])
        self.assertEqual(len(r["provenance"]["stage_receipts"]),4)
        critic={"assessment":"grounded","unsafe_claim_indices":[],
                "reason":"Only the observational association and study limits are asserted."}
        r=self.execute(critic=critic)
        self.assertEqual(r["result"],"candidate_answer_review_only")
        self.assertEqual(r["review_gate"],"NOT_APPROVED")

    def test_real_model_provider_failure_refuses_fallback_and_abstains(self):
        def down(prompt,phase):
            raise LLMUnavailable("Not authenticated")
        r=run(self.question,self.atlas,self.texts,down,
              mode="authenticated_live_model",provider_label="antigravity:test")
        self.assertEqual(r["result"],"abstained")
        self.assertEqual(r["reason"],"authenticated_model_unavailable_no_fallback")

    def test_disjoint_overlong_source_and_model_scope_limits(self):
        with self.assertRaisesRegex(ValueError,"SHA"):
            self.execute(texts={self.sid:BODY1+" wrong"})
        self.assertEqual(len(_windows(BODY1)),1)
        with self.assertRaisesRegex(ValueError,"longer"):
            _windows("x"*130000)
        stages=self.base_stages()
        stages["interpret_answer"]["claims"][0]["passage_id"]="P999"
        with self.assertRaisesRegex(ValueError,"never saw"):
            self.execute(stages)

    def test_manual_cli_requires_truthful_execution_mode_and_writes_receipt(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            atlas=root/"academic.json";atlas.write_text(json.dumps(self.atlas))
            originals=root/"source-texts";originals.mkdir()
            for sid,text in self.texts.items():
                (originals/(sid+".txt")).write_text(text)
            answers=root/"manual.json"
            answers.write_text(json.dumps(self.base_stages()))
            out=root/"answer.json"
            self.assertEqual(main(["--academic-atlas",str(atlas),
                "--original-text-dir",str(originals),
                "--question",self.question,
                "--responses",str(answers),"--output",str(out)]),0)
            saved=json.loads(out.read_text())
            self.assertEqual(saved["provenance"]["model_execution_mode"],
                "operator_supplied_model_responses_unverified")
            self.assertFalse(saved["provenance"]["independently_human_approved"])
            with self.assertRaisesRegex(ValueError,"overwrite"):
                main(["--academic-atlas",str(atlas),
                    "--original-text-dir",str(originals),
                    "--question",self.question,
                    "--responses",str(answers),"--output",str(out)])


if __name__=="__main__":
    unittest.main()
