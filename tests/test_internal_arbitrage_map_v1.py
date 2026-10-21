"""Self-arbitrage screening must separate three-layer hypotheses, tested bugs,
conditionally modeled physical buy/resale spreads and verified profits."""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
from io import StringIO
from contextlib import redirect_stdout
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
import unittest

from cite_refinery.internal_arbitrage import build,scenario_economics,markdown,SCHEMA,ECON_SCHEMA
from cite_refinery.layered_cli import main as app

ROOT=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"
def load(name):
    return json.loads((ROOT/name).read_text())
def sample():
    return {
      "id":"tw-used-console-repair-trial",
      "type":"used_electronics_repair_resale",
      "currency":"TWD","basis":"hypothetical",
      "upstream_reference":"UNVERIFIED: replace with dated, condition-matched acquisition listing and actual stock status",
      "downstream_reference":"UNVERIFIED: replace with realized transaction and after-fee sold price",
      "assumptions":{
        "purchase_price":2000,
        "success_sale_price":6000,
        "success_probability":"0.75",
        "success_sale_fees":500,
        "failure_recovery_value":500,
        "failure_disposal_cost":200,
        "inbound_shipping":100,
        "materials":400,
        "labor_hours":2,
        "labor_hourly_cost":300,
        "outbound_shipping":120,
        "storage":80,
        "tax_and_compliance":0,
        "contingency":200,
      }
    }

class InternalArbitrageMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas=load("three_layer_unified_atlas.json")
        cls.routes=load("operator_conversion_routes.json")

    def test_atlas_is_reused_widely_without_fourth_layer_or_commerce_promotion(self):
        out=build(self.atlas,self.routes)
        self.assertEqual(out["schema"],SCHEMA)
        self.assertEqual(out["conceptual_layers"],
                         ["practical","academic","implementation"])
        self.assertTrue(out["arbitrage_is_an_overlay_not_a_fourth_graph_layer"])
        self.assertEqual(out["coverage"]["atlas_problem_views"],21)
        self.assertEqual(out["coverage"]["full_three_layer_candidate_views"],7)
        self.assertEqual(out["coverage"]["tested_technical_repair_leads"],5)
        self.assertEqual(out["coverage"]["modeled_asset_spreads"],0)
        self.assertEqual(out["coverage"]["verified_profitable_arbitrage"],0)
        self.assertEqual(out["coverage"]["verified_buyers_or_customers"],0)
        self.assertFalse(out["graph_authority_promoted"])
        self.assertFalse(out["executed_trade_or_order"])
        all_ids=[r["id"] for r in out["atlas_problem_views"]]
        self.assertEqual(set(all_ids),set(self.atlas["problem_views"]))
        self.assertEqual(set(x["id"] for x in out["independent_technical_repair_leads"]),
                         set(x["id"] for x in self.routes["rows"]))
        self.assertTrue(all(x["economic_spread_verified"] is False
                            and x["do_not_join_to_atlas_by_repo_name_alone"]
                            for x in out["independent_technical_repair_leads"]))
        self.assertIn("No actual purchase",markdown(out))
        self.assertIn("NOT",markdown(out).upper())

    def test_unconnected_name_cannot_create_a_new_graph_link(self):
        altered=deepcopy(self.atlas)
        practical=next(k for k,v in altered["problem_views"].items()
                       if v.get("academic_nodes"))
        altered["problem_views"][practical]["implementation_links"].append({
            "id":"github:kobotoolbox/kpi","status":"model_generated_guess"})
        with self.assertRaisesRegex(ValueError,"source-backed implementation"):
            build(altered,self.routes)
        altered=deepcopy(self.atlas)
        altered["nodes"].append({"id":"new_layer:buyer","layer":"profit"})
        with self.assertRaisesRegex(ValueError,"fourth-layer"):
            build(altered,self.routes)

    def test_owner_strategy_is_not_automatically_a_new_graph_link_or_a_verified_market(self):
        targets=json.loads((ROOT/"owner_arbitrage_targets_v1.json").read_text())
        out=build(self.atlas,self.routes,owner_targets=targets)
        self.assertEqual(out["coverage"]["user_strategy_priorities"],6)
        by_id={x["id"]:x for x in out["owner_hypothesis_watchlist"]}
        self.assertEqual(by_id["taiwan_repair_resale"]["linked_practical_ids"],[])
        self.assertEqual(by_id["taiwan_repair_resale"]["linked_test_case_ids"],[])
        self.assertTrue(all(x["links_are_references_not_new_cross_layer_edges"] for x in by_id.values()))
        self.assertTrue(all(not x["profitable_spread_verified"] for x in by_id.values()))
        self.assertIn("Taiwan secondhand",markdown(out))
        bad=deepcopy(targets)
        bad["targets"][1]["linked_practical_ids"]=["problem:nonexistent"]
        with self.assertRaisesRegex(ValueError,"exact existing"):
            build(self.atlas,self.routes,owner_targets=bad)
        bad=deepcopy(targets)
        bad["targets"][0]["evidence_status"]="verified_profitable_arbitrage"
        with self.assertRaisesRegex(ValueError,"promoted"):
            build(self.atlas,self.routes,owner_targets=bad)

    def test_original_runtime_regressions_are_not_recommended_as_newly_missing(self):
        out=build(self.atlas,self.routes)
        by_id={x["id"]:x for x in out["independent_technical_repair_leads"]}
        self.assertIn("already reproduced",by_id["ofn_canada_map_bounds"]["next_evidence_test"])
        self.assertIn("already reproduced",by_id["foodsoft_order_quantity_rounding"]["next_evidence_test"])

    def test_operator_route_cannot_claim_paid_contract_or_deployment(self):
        amended=deepcopy(self.routes)
        amended["rows"][0]["buyer_verified"]=True
        with self.assertRaisesRegex(ValueError,"unsupported"):
            build(self.atlas,amended)
        amended=deepcopy(self.routes)
        amended["rows"][1]["technical"]["deployed_fit_verified"]=True
        with self.assertRaisesRegex(ValueError,"unsupported"):
            build(self.atlas,amended)

    def test_physical_arbitrage_expected_value_accounts_for_failure_labor_and_fees(self):
        v=scenario_economics(sample())
        self.assertEqual(v["success_branch_before_common_costs"],"5380.00")
        self.assertEqual(v["failure_branch_before_common_costs"],"300.00")
        self.assertEqual(v["expected_realization_before_purchase_and_common_costs"],"4110.00")
        self.assertEqual(v["shared_costs_including_labor_and_contingency"],"1380.00")
        self.assertEqual(v["conditional_break_even_purchase_price"],"2730.00")
        self.assertEqual(v["conditional_expected_net_after_all_modelled_costs"],"730.00")
        self.assertEqual(v["decision"],"RESEARCH_MORE_AND_VERIFY_QUOTES")
        self.assertFalse(v["positive_realized_spread_verified"])
        self.assertFalse(v["actual_buyer_verified"])
        self.assertFalse(v["available_inventory_verified"])
        obj=build(self.atlas,self.routes,{"schema":ECON_SCHEMA,"items":[sample()]})
        self.assertEqual(obj["coverage"]["modeled_asset_spreads"],1)
        self.assertEqual(obj["coverage"]["verified_profitable_arbitrage"],0)
        self.assertIn("730.00",markdown(obj))

    def test_reality_can_make_an_optimistic_spread_negative(self):
        c=sample()
        c["assumptions"]["success_probability"]="0.3"
        c["assumptions"]["failure_disposal_cost"]=900
        out=scenario_economics(c)
        self.assertEqual(out["decision"],"DO_NOT_BUY_AT_MODELED_PRICE")
        self.assertLess(Decimal(out["conditional_expected_net_after_all_modelled_costs"]),0)

    def test_missing_failure_path_or_unsupported_inputs_fail_closed(self):
        for edit in (
          lambda x:x["assumptions"].pop("failure_disposal_cost"),
          lambda x:x["assumptions"].update(success_probability="1.7"),
          lambda x:x["assumptions"].update(purchase_price="-200"),
          lambda x:x["assumptions"].update(success_sale_price="NaN"),
          lambda x:x["assumptions"].update(labor_hours=None),
          lambda x:x.update(currency="JPY"),
          lambda x:x.update(basis="verified_profit"),
          lambda x:x.update(type="stock_trading_bot"),
          lambda x:x.update(annual_revenue="2000000"),
        ):
            case=deepcopy(sample())
            edit(case)
            with self.assertRaises(ValueError):
                scenario_economics(case)

    def test_no_scenario_is_not_a_made_up_price_or_roi(self):
        a=build(self.atlas,self.routes)
        self.assertEqual(a["conditional_asset_spread_scenarios"],[])
        self.assertIn("No actual purchase",markdown(a))

    def test_canonical_cli_accepts_owner_strategy_and_failure_adjusted_spread(self):
        with TemporaryDirectory() as td:
            directory=Path(td)
            scenario_file=directory/"scenario.json"
            scenario_file.write_text(json.dumps({"schema":ECON_SCHEMA,"items":[sample()]}))
            output=StringIO()
            with redirect_stdout(output):
                app(["investigate","arbitrage-map",
                     "--atlas",str(ROOT/"three_layer_unified_atlas.json"),
                     "--operator-routes",str(ROOT/"operator_conversion_routes.json"),
                     "--owner-targets",str(ROOT/"owner_arbitrage_targets_v1.json"),
                     "--scenarios",str(scenario_file),
                     "--json-out",str(directory/"map.json"),
                     "--markdown-out",str(directory/"map.md")])
            printed=json.loads(output.getvalue())
            self.assertEqual(printed["coverage"]["user_strategy_priorities"],6)
            self.assertEqual(printed["coverage"]["modeled_asset_spreads"],1)
            self.assertEqual(printed["coverage"]["verified_profitable_arbitrage"],0)
            stored=json.loads((directory/"map.json").read_text())
            self.assertEqual(stored["conditional_asset_spread_scenarios"][0]["conditional_expected_net_after_all_modelled_costs"],"730.00")
            self.assertEqual(stored["coverage"]["verified_profitable_arbitrage"],0)
            self.assertIn("Our own capture hypotheses",(directory/"map.md").read_text())

    def test_canonical_cli_exports_whole_atlas_and_no_standalone_entrypoint(self):
        with TemporaryDirectory() as td:
            dir=Path(td)
            j=dir/"map.json"; m=dir/"map.md"
            output=StringIO()
            with redirect_stdout(output):
                app(["investigate","--workspace",str(dir/".cite-refinery-investigations"),
                     "arbitrage-map","--atlas",str(ROOT/"three_layer_unified_atlas.json"),
                     "--operator-routes",str(ROOT/"operator_conversion_routes.json"),
                     "--json-out",str(j),"--markdown-out",str(m)])
            printed=json.loads(output.getvalue())
            self.assertEqual(printed["coverage"]["atlas_problem_views"],21)
            self.assertEqual(printed["coverage"]["verified_profitable_arbitrage"],0)
            self.assertTrue(j.exists() and m.exists())
            self.assertFalse((dir/".cite-refinery-investigations").exists())
            self.assertEqual(json.loads(j.read_text())["schema"],SCHEMA)
            with self.assertRaisesRegex(ValueError,"overwrite"):
                app(["investigate","arbitrage-map",
                     "--atlas",str(ROOT/"three_layer_unified_atlas.json"),
                     "--operator-routes",str(ROOT/"operator_conversion_routes.json"),
                     "--json-out",str(j),"--markdown-out",str(m)])
            with (Path(__file__).resolve().parents[1]/"pyproject.toml").open("rb") as f:
                scripts=tomllib.load(f)["project"]["scripts"]
            self.assertEqual(len(scripts),50)
            self.assertNotIn("cite-refinery-arbitrage-map",scripts)

if __name__=="__main__":
    unittest.main()
