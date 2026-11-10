"""Channel-aware Chromebook trace: no fake signatures, contracts or price comparison."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cite_refinery.legal_codex_purchase_trace import evaluate, validate, semantic_packet
from cite_refinery.app import CiteRefinery
from cite_refinery.semantic import SemanticGraph

DATA = (Path(__file__).resolve().parents[1] /
        "examples/legal_codex_chromebook_purchase_channels_006.json")


class ChannelTraceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(DATA.read_text(encoding="utf-8"))

    def observation(self, ident):
        return next(o for o in self.fixture["observations"] if o["id"] == ident)

    def output(self, ident):
        return next(c for c in evaluate(self.fixture)["channels"] if c["channel_id"] == ident)

    def test_five_sources_eight_channels_thirteen_observations_eighteen_gaps(self):
        result = evaluate(self.fixture)
        self.assertEqual(result["source_count"], 5)
        self.assertEqual(len(result["channels"]), 8)
        self.assertEqual(result["observation_count"], 13)
        self.assertEqual(result["unobtained_records"], 18)
        self.assertFalse(result["cross_channel_transactions_reconciled"])
        self.assertFalse(result["corruption_or_state_loss_established_by_system"])

    def test_all_transaction_and_signatory_roles_unverified(self):
        result = evaluate(self.fixture)
        self.assertFalse(result["publication_authorized"])
        for channel in result["channels"]:
            self.assertEqual(channel["signatories_verified"], 0)
            self.assertEqual(channel["supplier_contracts_verified"], 0)
            self.assertEqual(channel["purchase_order_ids_verified"], 0)
            self.assertIsNone(channel["actual_decision_maker"])

    def test_separate_channels_and_years(self):
        channels = {c["channel_id"]: c for c in evaluate(self.fixture)["channels"]}
        self.assertEqual(channels["sd_siplah_order_2020"]["purchase_mode"],
                         "school_siplah_purchase")
        self.assertEqual(channels["smp_ecat_2020"]["purchase_mode"],
                         "directorate_ecatalog_purchase")
        self.assertEqual(channels["dak_laptop_2022"]["purchase_mode"],
                         "dak_regional_ecatalog")
        self.assertEqual(channels["dak_laptop_2022"]["year"], 2022)
        self.assertTrue(evaluate(self.fixture)["2022_catalogue_ceiling_is_not_2020_purchase_price"])

    def test_money_is_not_arbitrarily_normalized_to_laptop_price(self):
        result = evaluate(self.fixture)
        self.assertTrue(result["2020_school_grant_is_not_laptop_unit_price"])
        self.assertTrue(result["2021_output_package_count_is_not_independent_usage_measure"])
        self.assertIsNone(self.fixture["state_loss_estimate"])
        metrics = {
            x["metric"]["kind"]: x["metric"]["value"]
            for c in result["channels"] for x in c["source_observations"] if x["metric"]
        }
        self.assertEqual(metrics["grant_allocation_per_school_idr"], 88250000)
        self.assertEqual(metrics["announced_package_allocation_idr"], 95000000)
        self.assertEqual(metrics["framework_unit_ceiling_idr"], 5550000)

    def test_2021_month_precision_not_given_arbitrary_reporting_day(self):
        self.assertEqual(next(s for s in self.fixture["sources"]
                              if s["id"] == "sd_lakip_2021")["source_date"], "2022-01")
        self.assertEqual(self.output("sd_apbn_grant_2021")["source_observations"][0]["source_date"],
                         "2022-01")

    def test_2022_vendor_listing_cannot_prove_2020_award(self):
        result = evaluate(self.fixture)
        self.assertTrue(result["later_vendor_marketplace_designation_is_not_2020_contract_award"])
        vendor = self.output("bhinneka_marketplace_2022")
        self.assertEqual(vendor["purchase_mode"], "marketplace_registration_not_purchase")
        self.assertFalse(vendor["transaction_price_verified"])

    def test_fake_purchase_id_blocked(self):
        self.fixture["verified_procurement_packages"] = ["imagined_id"]
        with self.assertRaisesRegex(ValueError, "verified package"):
            validate(self.fixture)

    def test_fake_signed_officer_blocked(self):
        self.fixture["channels"][0]["actual_signing_officer"] = "Named public official"
        with self.assertRaisesRegex(ValueError, "cannot invent"):
            validate(self.fixture)

    def test_fake_signed_contract_blocked(self):
        self.fixture["verified_contracts"] = [{"contract":"fake"}]
        with self.assertRaisesRegex(ValueError, "signed contract"):
            validate(self.fixture)

    def test_injected_state_loss_blocked(self):
        self.fixture["state_loss_estimate"] = 100000000
        with self.assertRaisesRegex(ValueError, "fiscal loss"):
            validate(self.fixture)

    def test_future_transaction_placed_before_source_fails(self):
        self.observation("sd_2020_grant_unit")["event_date"] = "2024-01-01"
        with self.assertRaises(ValueError):
            validate(self.fixture)

    def test_2022_price_ceiling_cannot_backdate_to_2020(self):
        o = self.observation("dak_2022_laptop_ceiling")
        o["event_date"] = "2020-06-30"
        with self.assertRaisesRegex(ValueError, "wrong procurement year"):
            validate(self.fixture)
        o["event_date"] = "2022-07-28"
        o["channel_id"] = "sd_apbn_grant_2020"
        with self.assertRaisesRegex(ValueError, "wrong procurement year"):
            validate(self.fixture)

    def test_official_ministry_message_not_prosecution_allegation(self):
        self.observation("sd_2020_grant_unit")["stance"] = "prosecutor_allegation"
        with self.assertRaisesRegex(ValueError, "misattributed"):
            validate(self.fixture)

    def test_claims_stay_source_attributed_in_semantic_packet(self):
        packet = semantic_packet(self.fixture)
        self.assertEqual(packet["schema"], "cite_refinery.semantic_graph.v1")
        self.assertTrue(all(n["layer"] == "neutral" for n in packet["nodes"]))
        self.assertTrue(all(e["status"] == "candidate" for e in packet["edges"]))
        self.assertFalse(any(e["relation"] in {"CORRUPTED", "COLLUDED", "PAID"}
                             for e in packet["edges"]))
        self.assertEqual(len(packet["edges"]), 2 * 13)
        with tempfile.TemporaryDirectory() as tmp:
            app = CiteRefinery(tmp)
            proj = app.init_project("Procurement channel trace", "Evidence gates")
            graph = SemanticGraph(app.store)
            preview = graph.preview_packet(proj.id, packet)
            self.assertFalse(preview["authority_boundary_warnings"])
            receipt = graph.ingest_packet(
                proj.id, packet, expected_state_digest=preview["state_digest"])
            self.assertEqual(len(receipt["edge_ids"]), 26)
            state = app.store.load()
            self.assertTrue(all(state["semantic_edges"][k]["status"] == "candidate"
                                for k in receipt["edge_ids"]))


if __name__ == "__main__":
    unittest.main()
