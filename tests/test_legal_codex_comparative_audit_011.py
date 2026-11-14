"""Milestone 011 comparative pilot regression and adversarial gates."""
import copy
import json
from pathlib import Path
import unittest

from cite_refinery.legal_codex_comparative_audit import (
    evaluate, validate, semantic_packet,
)

SEED = Path(__file__).resolve().parents[1] / "examples/legal_codex_comparative_audit_011.json"


class ComparativeAudit011Tests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SEED.read_text(encoding="utf-8"))

    def find(self, collection, ident):
        return next(x for x in self.data[collection] if x["id"] == ident)

    def test_real_two_jurisdiction_pilot_is_source_attributed(self):
        out = evaluate(self.data)
        self.assertEqual(out["case_count"], 2)
        self.assertEqual(out["source_locator_count"], 5)
        self.assertEqual(out["institution_count"], 7)
        self.assertEqual(out["attributed_finding_count"], 5)
        self.assertEqual(out["intervention_count"], 5)
        self.assertEqual(out["comparison_count"], 3)
        self.assertFalse(out["source_byte_integrity_verified"])
        self.assertFalse(out["independent_editorial_review"])
        self.assertFalse(out["named_person_culpability_established"])
        self.assertFalse(out["causal_policy_effect_estimated"])
        self.assertFalse(out["cross_jurisdiction_law_applied"])
        self.assertFalse(out["publication_authorized"])
        self.assertEqual({c["jurisdiction"] for c in out["cases"]},
                         {"England and Wales", "Netherlands"})
        self.assertTrue(all(
            row["time_relative_to_failure"] == "post_failure_period"
            for c in out["cases"] for row in c["interventions"]))

    def test_comparisons_are_analogies_not_foreign_rules(self):
        out = evaluate(self.data)
        self.assertEqual([x["transfer_status"] for x in out["comparisons"]],
                         ["analogy_only", "non_equivalent_remedies", "analogy_only"])
        self.assertTrue(all(x["foreign_law_applicable"] is False
                            and x["legal_equivalence_established"] is False
                            and x["policy_effect_estimate"] is None
                            for x in out["comparisons"]))
        self.assertEqual(len(out["cases"][0]["unresolved_record_requests"]), 2)
        self.assertEqual(len(out["cases"][1]["unresolved_record_requests"]), 2)

    def test_no_fake_source_archive_or_editorial_signoff(self):
        self.data["original_documents_archived"] = True
        with self.assertRaisesRegex(ValueError, "unarchived"):
            validate(self.data)
        self.data["original_documents_archived"] = False
        self.data["independent_editorial_review"] = True
        with self.assertRaisesRegex(ValueError, "independent reviewer"):
            validate(self.data)

    def test_fake_source_original_rejected(self):
        self.find("sources", "s_uk_act")["original_bytes_verified"] = True
        with self.assertRaisesRegex(ValueError, "source page"):
            validate(self.data)

    def test_source_not_journalism_laundered_into_official(self):
        self.find("sources", "s_nl_dpa")["url"] = "https://example.com/fine"
        with self.assertRaisesRegex(ValueError, "host/type provenance"):
            validate(self.data)

    def test_official_host_must_match_document_class(self):
        self.find("sources", "s_nl_dpa")["url"] = "https://www.legislation.gov.uk/example"
        with self.assertRaisesRegex(ValueError, "host/type provenance"):
            validate(self.data)

    def test_foreign_source_scope_cannot_cover_local_case(self):
        self.find("sources", "s_uk_act")["jurisdictions"] = ["Netherlands"]
        with self.assertRaisesRegex(ValueError, "source jurisdiction"):
            validate(self.data)

    def test_source_cannot_be_assigned_to_other_case(self):
        self.find("findings", "f_nl_dpa")["source_id"] = "s_uk_act"
        with self.assertRaisesRegex(ValueError, "crossed case"):
            validate(self.data)

    def test_source_cannot_impersonate_a_different_institutional_power(self):
        self.find("findings", "f_uk_act")["kind"] = "regulatory_determination"
        with self.assertRaisesRegex(ValueError, "different type"):
            validate(self.data)

    def test_named_institution_must_be_in_same_case(self):
        self.find("findings", "f_uk_ccrc")["institution_id"] = "nl_tax_authority"
        with self.assertRaisesRegex(ValueError, "crossed case"):
            validate(self.data)

    def test_official_act_cannot_be_backdated_into_pre_harm_prevention(self):
        self.find("interventions", "a_uk_act")["effective_on"] = "2000-01-01"
        with self.assertRaisesRegex(ValueError, "backdated"):
            validate(self.data)

    def test_republication_date_cannot_backdate_finding(self):
        self.find("findings", "f_uk_ccrc")["observed_on"] = "1999-01-01"
        with self.assertRaisesRegex(ValueError, "backdating"):
            validate(self.data)

    def test_future_legal_action_rejected(self):
        self.find("sources", "s_uk_act")["published_on"] = "2028-01-01"
        with self.assertRaisesRegex(ValueError, "future official source"):
            validate(self.data)

    def test_cross_jurisdiction_intervention_not_legal_transplant(self):
        self.find("interventions", "a_uk_act")["jurisdictions"].append("Netherlands")
        with self.assertRaisesRegex(ValueError, "jurisdiction"):
            validate(self.data)

    def test_fine_is_not_individual_compensation(self):
        self.find("interventions", "a_nl_dpa")["individual_remedy_proven"] = True
        with self.assertRaisesRegex(ValueError, "unverified remedy"):
            validate(self.data)

    def test_regulatory_fine_not_conviction_quashing(self):
        self.find("interventions", "a_nl_dpa")["power"] = "criminal_conviction_relief"
        with self.assertRaisesRegex(ValueError, "power or jurisdiction"):
            validate(self.data)

    def test_no_unmeasured_effect_sizes(self):
        self.find("comparisons", "cmp_03_scrutiny")["effect_size"] = 0.73
        with self.assertRaisesRegex(ValueError, "causal effect"):
            validate(self.data)

    def test_unsupported_comparability_tag_rejected(self):
        self.find("comparisons", "cmp_02_redress")["failure_mode"] = "procurement_collusion"
        with self.assertRaisesRegex(ValueError, "shared failure mode"):
            validate(self.data)

    def test_cross_case_mechanism_swap_rejected(self):
        self.find("comparisons", "cmp_02_redress")["right_intervention_id"] = "a_uk_ccrc"
        with self.assertRaisesRegex(ValueError, "distinct case-local"):
            validate(self.data)

    def test_competing_policy_actions_do_not_imply_criminal_guilt(self):
        self.find("findings", "f_nl_dpa")["independent_causal_effect"] = 1.0
        with self.assertRaisesRegex(ValueError, "overclaimed"):
            validate(self.data)

    def test_evidence_gaps_both_jurisdictions(self):
        self.data["evidence_gaps"] = [
            g for g in self.data["evidence_gaps"] if g["case_id"] == "horizon"
        ]
        with self.assertRaisesRegex(ValueError, "each case"):
            validate(self.data)

    def test_graph_is_candidate_only_and_not_culpability(self):
        result = evaluate(self.data)
        packet = semantic_packet(self.data, result)
        self.assertEqual(packet["schema"], "cite_refinery.semantic_graph.v1")
        self.assertTrue(packet["edges"])
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in
                             {"GUILTY", "SIGNED", "PAID", "CAUSES", "LEGAL_RULE_APPLIES"}
                             for e in packet["edges"]))
        comparisons = [e for e in packet["edges"]
                       if e["relation"] == "COMPARABLE_MECHANISM_CANDIDATE"]
        self.assertEqual(len(comparisons), 3)
        self.assertTrue(all(e["provenance"]["foreign_law_applicable"] is False
                            for e in comparisons))

    def test_stale_result_rejected(self):
        out = evaluate(self.data)
        mutated = copy.deepcopy(self.data)
        self.find("findings", "f_nl_dpa")["statement"] += " Supplement."
        with self.assertRaisesRegex(ValueError, "stale"):
            semantic_packet(self.data, out)


if __name__ == "__main__":
    unittest.main()
