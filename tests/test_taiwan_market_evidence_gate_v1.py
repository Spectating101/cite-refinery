"""Real public Taiwan ask-listing evidence: do not market an invalid trade."""
from __future__ import annotations
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from cite_refinery.internal_arbitrage import (
    MARKET_SCHEMA,screen_market,build,markdown
)
from cite_refinery.layered_cli import main as cli

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"
def get(name):
    return json.loads((ROOT/name).read_text())

class TaiwanMarketGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=get("taiwan_market_listing_evidence_20261021.json")

    def test_actual_indexed_and_direct_sources_never_count_as_verified_trades(self):
        out=screen_market(self.data)
        self.assertEqual(out["listed_observations"],9)
        self.assertEqual(out["source_only_cached_search_items"],5)
        self.assertEqual(len(out["rejected_unavailable_items"]),2)
        self.assertEqual(out["verified_realized_comparable_sales"],0)
        self.assertEqual(out["observed_market_quotes_available_for_current_checkout"],0)
        self.assertEqual(out["authorized_trades"],0)
        self.assertEqual(out["verified_profitable_arbitrage"],0)
        cases={x["candidate_id"]:x for x in out["candidate_asking_comparisons"]}
        self.assertEqual(cases["switch_lite_broken_blue_screen"]["headline_asking_gap_twd"],"550.00")
        self.assertEqual(cases["switch_lite_broken_blue_screen"]["illustrative_after_base_transaction_fee_gap_twd"],"490.00")
        self.assertEqual(cases["three_ds_broken_no_boot_1950"]["headline_asking_gap_twd"],"2000.00")
        self.assertEqual(cases["three_ds_broken_charge_lr_2800"]["headline_asking_gap_twd"],"1150.00")
        self.assertTrue(all(x["decision"]=="NO_BUY_EVIDENCE_INSUFFICIENT" for x in cases.values()))
        self.assertTrue(all(x["live_qualified_arbitrage"] is False for x in cases.values()))

    def test_repair_service_is_not_an_acquisition_or_blue_screen_repair_bid(self):
        report=screen_market(self.data)
        self.assertEqual(report["repair_or_part_price_observations"],1)
        pairs=report["candidate_asking_comparisons"]
        self.assertTrue(all(x["candidate_id"]!="switch_lite_screen_service_2280" for x in pairs))
        self.assertTrue(all(x["comparison_source_id"]!="switch_lite_screen_service_2280" for x in pairs))

    def test_fake_verified_sale_or_inventory_fails_closed(self):
        for mutate in (
            lambda x:x["records"][0].update(proof_of_completed_sale=True),
            lambda x:x["records"][0].update(physical_stock_verified=True),
            lambda x:x["source_handling"].update(orders_placed=True),
            lambda x:x["source_handling"].update(completed_sale_records=1),
            lambda x:x["records"][0].update(source_state="source_open_verified_checkout"),
            lambda x:x["records"][3].update(source_state="active_listing_page"),
            lambda x:x["records"][3].update(url="https://localhost/metadata"),
            lambda x:x["records"][3].update(displayed_twd=-300),
            lambda x:x["records"][3].update(displayed_twd="NaN"),
            lambda x:x["records"][3].update(authorized_profit_claim="real"),
            lambda x:x.update(observed_on="2099-12-31"),
        ):
            trial=deepcopy(self.data)
            mutate(trial)
            with self.assertRaises(ValueError):
                screen_market(trial)

    def test_duplicate_source_identity_and_cross_model_mismatch_block_inflation(self):
        trial=deepcopy(self.data)
        trial["records"][4]["id"]=trial["records"][3]["id"]
        with self.assertRaisesRegex(ValueError,"Repeated"):
            screen_market(trial)
        trial=deepcopy(self.data)
        for x in trial["records"]:
            if x["role"]=="working_device_ask":
                x["model"]="nintendo_switch_oled" if x["model"]=="nintendo_switch_lite" else "new_3ds_ll"
        report=screen_market(trial)
        self.assertTrue(all(x["comparison_state"]=="no_model_matched_asking_reference"
                            for x in report["candidate_asking_comparisons"]))
        self.assertEqual(report["verified_profitable_arbitrage"],0)

    def test_full_21_view_map_integrates_snapshot_without_new_graph_edges(self):
        j=build(get("three_layer_unified_atlas.json"),
                get("operator_conversion_routes.json"),
                owner_targets=get("owner_arbitrage_targets_v1.json"),
                market_snapshot=self.data)
        self.assertEqual(j["coverage"]["atlas_problem_views"],21)
        self.assertEqual(j["coverage"]["user_strategy_priorities"],6)
        self.assertEqual(j["coverage"]["public_market_observations"],9)
        self.assertEqual(j["coverage"]["verified_profitable_arbitrage"],0)
        self.assertFalse(j["graph_authority_promoted"])
        self.assertIn("Public Taiwan listing sample",markdown(j))
        self.assertIn("NO_BUY_EVIDENCE_INSUFFICIENT",markdown(j))

    def test_installed_command_accepts_market_evidence_without_writing_workspace(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            args=["investigate","--workspace",str(root/"phantom"),
                  "arbitrage-map","--atlas",str(ROOT/"three_layer_unified_atlas.json"),
                  "--operator-routes",str(ROOT/"operator_conversion_routes.json"),
                  "--owner-targets",str(ROOT/"owner_arbitrage_targets_v1.json"),
                  "--market-evidence",str(ROOT/"taiwan_market_listing_evidence_20261021.json"),
                  "--json-out",str(root/"map.json"),
                  "--markdown-out",str(root/"map.md")]
            buf=StringIO()
            with redirect_stdout(buf):
                cli(args)
            summary=json.loads(buf.getvalue())
            self.assertEqual(summary["coverage"]["public_market_observations"],9)
            self.assertFalse((root/"phantom").exists())
            result=json.loads((root/"map.json").read_text())
            self.assertEqual(result["source_checked_market_screen"]["verified_profitable_arbitrage"],0)
            with self.assertRaisesRegex(ValueError,"overwrite"):
                cli(args)

if __name__=="__main__":
    unittest.main()
