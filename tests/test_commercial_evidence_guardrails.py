"""Synthetic attestation tests: no real buyer, contract, or commercial claims."""
from __future__ import annotations

from datetime import date, timedelta
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from cite_refinery.commercial_guardrails import KEY_ENV, digest
from cite_refinery.opportunity_conversion import evaluate

ROOT = Path(__file__).resolve().parents[1] / "research_materials/opportunity_conversion"
KEY = "TEST-ONLY-LOCAL-REVIEWER-KEY-1234567890-not-for-production"


def fixture():
    return json.loads((ROOT / "ofn-paid-contributor-route.json").read_text("utf-8"))


def attest(purpose, case, *, url, subject, buyer="buyer-example", extra=None):
    payload = {
        "schema": "cite_refinery.commercial_review_attestation.v1",
        "purpose": purpose,
        "case_id": case["case_id"],
        "subject_sha256": digest(subject),
        "buyer_id": buyer,
        "reviewer_id": "authorized-reviewer-test-only",
        "evidence_url": url,
        "evidence_sha256": "b" * 64,
        "reviewed_on": date.today().isoformat(),
        "expires_on": (date.today() + timedelta(days=30)).isoformat(),
        **(extra or {}),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {
        "payload": payload,
        "signature": hmac.new(KEY.encode(), raw, hashlib.sha256).hexdigest(),
    }


def synthetic_case():
    c = fixture()
    c["fit"]["verification"] = "executed_local"  # synthetic fixture, not real execution
    c["fit"]["execution_evidence"] = [{"url": "https://example.org/synthetic-ci-execution-receipt", "claim": "Test-only invented execution receipt for verifying signed review custody.", "status": "reviewed"}]
    c["market"]["demand_status"] = "signed_commitment"
    c["market"]["signals"] = [{
        "url": "https://procurement.example.org/synthetic-private-agreement",
        "claim": "TEST-ONLY hypothetical agreement for validating the gate mechanics, not a real purchase.",
        "status": "reviewed",
        "kind": "signed_contract",
    }]
    c["competitive_alternatives"] = [{
        "name": "Competing map maintenance contractor",
        "url": "https://example.org/competing-map-maintenance",
        "scope": "direct",
    }]
    return c


def add_attestations(c):
    c["fit"]["execution_attestation"] = attest(
        "technical_execution", c,
        url=c["fit"]["execution_evidence"][0]["url"],
        subject={k: v for k, v in c["fit"].items() if k != "execution_attestation"},
    )
    c["market"]["demand_attestation"] = attest(
        "buyer_demand", c, url=c["market"]["signals"][0]["url"],
        subject=c["market"]["signals"], extra={"demand_status": c["market"]["demand_status"]},
    )
    c["competitive_review"] = {
        "assessment": "buyer_verified_differentiation",
        "attestation": attest(
            "competitive_differentiation", c,
            url=c["competitive_alternatives"][0]["url"],
            subject=c["competitive_alternatives"],
            extra={"assessment": "buyer_verified_differentiation"},
        ),
    }
    return c


class CommercialEvidenceGuardTests(unittest.TestCase):
    def test_public_bug_labeled_contract_stays_evidence_lead(self):
        c = fixture()
        c["fit"]["verification"] = "executed_local"
        c["market"]["demand_status"] = "signed_commitment"
        c["market"]["signals"] = [{
            "url": "https://github.com/openfoodfoundation/openfoodnetwork/issues/14924",
            "claim": "Bogus assertion: this issue is a signed commercial agreement.",
            "status": "reviewed", "kind": "signed_contract",
        }]
        with patch.dict(os.environ, {KEY_ENV: ""}):
            report = evaluate(c)
        self.assertEqual(report["buyer"]["verified_demand_status"], "unverified_claim")
        self.assertEqual(report["buyer"]["demand_status"], "unverified_claim")
        self.assertEqual(report["buyer"]["claimed_demand_status"], "signed_commitment")
        self.assertFalse(report["buyer"]["demand_attestation_valid"])
        self.assertEqual(report["readiness"], "evidence_lead_only")

    def test_even_signed_github_bug_cannot_be_a_contract(self):
        c = synthetic_case()
        c["market"]["signals"][0]["url"] = "https://github.com/openfoodfoundation/openfoodnetwork/issues/14924"
        c["market"]["signals"][0]["claim"] = "Intentionally false commercial-contract description for a genuine public bug."
        c = add_attestations(c)
        with patch.dict(os.environ, {KEY_ENV: KEY}):
            result = evaluate(c)
        self.assertEqual(result["buyer"]["demand_status"], "unverified_claim")
        self.assertFalse(result["buyer"]["demand_attestation_valid"])
        self.assertEqual(result["readiness"], "evidence_lead_only")
        self.assertIn("GitHub issue", result["buyer"]["verification_limitation"])

    def test_alternative_changes_recommended_action(self):
        c = json.loads((ROOT / "pv-independent-rooftop-performance-audit.json").read_text())
        self.assertIn("Interview", evaluate(c)["recommended_next_test"])
        c["competitive_alternatives"] = [{
            "name": "Solargis PV Performance Assessment",
            "url": "https://www.solargis.com/services/pv-performance-assessment",
            "scope": "direct",
        }]
        result = evaluate(c)
        self.assertEqual(result["competitive_review"]["alternatives"][0]["scope"], "direct")
        self.assertIn("Compare the existing substitutes", result["recommended_next_test"])
        self.assertEqual(result["readiness"], "evidence_lead_only")

    def test_signed_attestations_can_only_support_conditional_pilot(self):
        c = add_attestations(synthetic_case())
        with patch.dict(os.environ, {KEY_ENV: KEY}):
            result = evaluate(c)
        self.assertEqual(result["readiness"], "candidate_for_paid_pilot_subject_to_contract_and_rights")
        self.assertTrue(result["buyer"]["demand_attestation_valid"])
        self.assertTrue(result["competitive_review"]["attestation_valid"])
        self.assertTrue(result["cross_layer_fit"]["execution_attestation_valid"])
        self.assertNotEqual(result["readiness"], "revenue_verified")
        self.assertFalse(c["compliance"]["deployment_authorized"])

    def test_unverified_execution_prevents_paid_pilot_even_with_verified_buyer(self):
        c = add_attestations(synthetic_case())
        del c["fit"]["execution_attestation"]
        with patch.dict(os.environ, {KEY_ENV: KEY}):
            report = evaluate(c)
        self.assertTrue(report["buyer"]["demand_attestation_valid"])
        self.assertTrue(report["competitive_review"]["attestation_valid"])
        self.assertFalse(report["cross_layer_fit"]["execution_attestation_valid"])
        self.assertEqual(report["readiness"], "evidence_lead_only")

    def test_missing_key_mismatched_evidence_and_tampering_fail_closed(self):
        c = add_attestations(synthetic_case())
        with patch.dict(os.environ, {KEY_ENV: ""}):
            self.assertEqual(evaluate(c)["readiness"], "evidence_lead_only")
        variants = []
        a = copy.deepcopy(c)
        a["market"]["signals"][0]["claim"] += " tamper"
        variants.append(a)
        a = copy.deepcopy(c)
        a["market"]["demand_attestation"]["payload"]["buyer_id"] = "different-buyer"
        variants.append(a)
        a = copy.deepcopy(c)
        a["competitive_alternatives"][0]["url"] += "/moved"
        variants.append(a)
        a = copy.deepcopy(c)
        a["competitive_review"]["assessment"] = "unresolved"
        variants.append(a)
        a = copy.deepcopy(c)
        a["competitive_review"]["attestation"]["payload"]["assessment"] = "unresolved"
        variants.append(a)
        with patch.dict(os.environ, {KEY_ENV: KEY}):
            for variant in variants:
                with self.subTest(variant=variants.index(variant)):
                    self.assertEqual(evaluate(variant)["readiness"], "evidence_lead_only")

    def test_competitor_review_cannot_use_a_different_buyer(self):
        c = add_attestations(synthetic_case())
        c["competitive_review"]["attestation"] = attest(
            "competitive_differentiation", c,
            url=c["competitive_alternatives"][0]["url"],
            subject=c["competitive_alternatives"],
            buyer="another-buyer",
            extra={"assessment": "buyer_verified_differentiation"},
        )
        with patch.dict(os.environ, {KEY_ENV: KEY}):
            report = evaluate(c)
        self.assertTrue(report["buyer"]["demand_attestation_valid"])
        self.assertFalse(report["competitive_review"]["attestation_valid"])
        self.assertEqual(report["readiness"], "evidence_lead_only")

    def test_stale_attestation_and_self_reported_competition_do_not_promote(self):
        c = add_attestations(synthetic_case())
        c["competitive_review"]["attestation"]["payload"]["expires_on"] = (
            date.today() - timedelta(days=1)
        ).isoformat()
        with patch.dict(os.environ, {KEY_ENV: KEY}):
            self.assertEqual(evaluate(c)["readiness"], "evidence_lead_only")
        c = add_attestations(synthetic_case())
        del c["competitive_review"]["attestation"]
        with patch.dict(os.environ, {KEY_ENV: KEY}):
            self.assertEqual(evaluate(c)["readiness"], "evidence_lead_only")

    def test_malformed_competitor_and_duplicate_or_unscoped_source_rejected(self):
        c = synthetic_case()
        c["competitive_alternatives"].append(copy.deepcopy(c["competitive_alternatives"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate competitor"):
            evaluate(c)
        c = synthetic_case()
        del c["competitive_alternatives"][0]["scope"]
        with self.assertRaisesRegex(ValueError, "direct/partial/adjacent"):
            evaluate(c)


if __name__ == "__main__":
    unittest.main()
