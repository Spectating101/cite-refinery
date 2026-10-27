"""Deterministic no-network hardware-market-radar regression tests."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from cite_refinery.hardware_market_radar import ROOT, evaluate, main

DATA = ROOT / "research_materials/opportunity_conversion"


def read(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def fixture() -> tuple[dict, dict, dict, dict]:
    return (
        read("hardware_market_universe_64_unverified_20261028.json"),
        read("hardware_12_case_post_research_evidence_queue_20261028.json"),
        read("hardware_radar_observations_seed_20261028.json"),
        read("hardware_radar_capabilities_20261028.json"),
    )


class HardwareMarketRadarTests(unittest.TestCase):
    def board(self, *, observed_on="2026-10-28"):
        return evaluate(*fixture(), as_of=observed_on,
                        supplier_manifest=read("hardware_radar_supplier_candidates_20261028.json"))

    def test_real_casebook_runs_but_never_invents_businesses(self):
        r = self.board()
        s = r["summary"]
        self.assertEqual(r["schema"], "cite_refinery.hardware_market_radar.v1")
        self.assertEqual(s["catalog_concepts"], 64)
        self.assertEqual(s["catalog_sectors"], 16)
        self.assertEqual(s["screened_cases"], 12)
        self.assertEqual(s["source_observations"], 12)
        self.assertEqual(s["qualified_opportunities"], 0)
        self.assertEqual(s["verified_supplier_quotes"], 0)
        self.assertEqual(s["verified_customer_payments"], 0)
        self.assertEqual(s["physically_validated_builds"], 0)
        self.assertEqual(r["change_detection"]["state"], "BASELINE")
        self.assertTrue(all(x["landed_unit_cost"] is None and x["net_margin"] is None
                            and not x["local_shortage_proven"] and not x["delivery_authorized"]
                            for x in r["cases"]))

    def test_competition_and_weak_reference_classified_correctly(self):
        rows = {x["case_id"]: x for x in self.board()["cases"]}
        self.assertEqual(rows["CASE-02"]["named_local_sellers"], 2)
        self.assertEqual(rows["CASE-02"]["market_offer_state"], "PUBLISHED_LOCAL_OFFER_EXISTS")
        self.assertEqual(rows["CASE-04"]["named_local_sellers"], 0)  # Global robot seller != local supply
        self.assertEqual(rows["CASE-06"]["named_local_sellers"], 0)  # Historic != current
        self.assertEqual(rows["CASE-07"]["named_local_sellers"], 0)  # Sourcing service != exact part stock
        self.assertEqual(rows["CASE-12"]["observation_count"], 0)
        self.assertTrue(all(x["market_offer_state"] in {"PUBLISHED_LOCAL_OFFER_EXISTS", "UNKNOWN_NO_LOCAL_EVIDENCE"}
                            for x in rows.values()))
        self.assertTrue(all(not x["local_shortage_proven"] for x in rows.values()))

    def test_capability_cross_sector_reuse_is_not_compatibility(self):
        b = self.board()
        self.assertGreater(len(b["cross_sector_reuse"]), 1)
        edges = b["candidate_capability_edges"]
        self.assertTrue(any(x["case_id"] == "CASE-03" and x["capability_id"] == "hs_firmware_scaffold" for x in edges))
        self.assertTrue(any(x["case_id"] == "CASE-05" and x["capability_id"] == "hs_firmware_scaffold" for x in edges))
        self.assertTrue(all(x["relation"] == "TAG_OVERLAP_CANDIDATE_ONLY"
                            and not x["verified_design_compatibility"] for x in edges))
        self.assertTrue(all(not x["verified_reuse"] for x in b["cross_sector_reuse"]))
        self.assertTrue(all(not x["physically_verified"] and not x["procurement_qualified"]
                            for x in b["capabilities"]))


    def test_actual_supplier_catalog_is_unqualified_and_cross_sector(self):
        r = self.board()
        self.assertEqual(r["summary"]["unqualified_supplier_directory_entries"], 14)
        self.assertGreater(r["summary"]["candidate_supplier_case_links"], 20)
        self.assertTrue(any(x["supplier_id"] == "dfrobot" and x["case_id"] == "CASE-11"
                            for x in r["candidate_supplier_edges"]))
        self.assertTrue(any(x["supplier_id"] == "petoi" and x["case_id"] == "CASE-04"
                            for x in r["candidate_supplier_edges"]))
        self.assertTrue(all(not x["verified_sku_availability"] and
                            not x["verified_quote_or_moq"] and
                            not x["verified_serves_target_market"] and
                            not x["procurement_qualified"]
                            for x in r["supplier_candidates"]))
        self.assertTrue(all(x["relation"] == "CATALOG_TAG_OVERLAP_ONLY" and
                            not x["qualified_supplier_quote"]
                            for x in r["candidate_supplier_edges"]))

    def test_untrusted_supplier_manifest_fails_closed(self):
        supplier_manifest = read("hardware_radar_supplier_candidates_20261028.json")
        cat, queue, obs, cap = fixture()
        supplier_manifest["suppliers"][0]["status"] = "qualified"
        with self.assertRaisesRegex(ValueError, "self-certify"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28",
                     supplier_manifest=supplier_manifest)
        supplier_manifest = read("hardware_radar_supplier_candidates_20261028.json")
        supplier_manifest["suppliers"].append(deepcopy(supplier_manifest["suppliers"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate supplier"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28",
                     supplier_manifest=supplier_manifest)

    def test_repeatability_and_snapshot_change_semantics(self):
        cat, queue, obs, cap = fixture()
        first = evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        repeat = evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        self.assertEqual(first, repeat)
        updated = deepcopy(obs)
        updated["observations"][0]["price"]["amount"] = "8700000"
        updated["observations"].pop(1)
        updated["observations"].append({
            "observation_id": "new_local_seller_20261028", "case_id": "CASE-12",
            "kind": "local_offer", "market": "TW", "seller": "Example seller",
            "product": "Dummy demonstration SKU",
            "observed_on": "2026-10-28", "source_url": "https://example.com/device",
            "evidence_state": "public_listing_unverified", "exact_variant_matched": False,
            "price": None,
        })
        second = evaluate(cat, queue, updated, cap, as_of="2026-10-28", previous=first)
        ch = second["change_detection"]
        self.assertEqual(ch["state"], "COMPARED_WITH_PREVIOUS_SNAPSHOT")
        self.assertEqual(len(ch["new"]), 1)
        self.assertEqual(len(ch["revised"]), 1)
        self.assertEqual(len(ch["missing_from_input_not_stockout"]), 1)
        self.assertEqual(second["summary"]["qualified_opportunities"], 0)
        self.assertFalse(next(x for x in second["cases"] if x["case_id"] == "CASE-12")["local_shortage_proven"])

    def test_price_and_scope_never_infer_arbitrage(self):
        cat, queue, obs, cap = fixture()
        obs["observations"][0]["price"] = {"amount": "99999.99", "currency": "IDR"}
        result = evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        self.assertEqual(result["summary"]["qualified_opportunities"], 0)
        self.assertTrue(all(x["net_margin"] is None for x in result["cases"]))

    def test_reject_untrusted_buyer_or_stock_certification(self):
        for field in ("paid_sale_verified", "supplier_qualified", "buyer_verified", "stock_verified"):
            with self.subTest(field=field):
                cat, queue, obs, cap = fixture()
                obs["observations"][0][field] = True
                with self.assertRaisesRegex(ValueError, "self-certify"):
                    evaluate(cat, queue, obs, cap, as_of="2026-10-28")

    def test_reject_false_financial_field_and_bad_url(self):
        for field, value in (("expected_profit", "99999"), ("verified_net_margin", 0.95)):
            with self.subTest(field=field):
                cat, queue, obs, cap = fixture()
                obs["observations"][0][field] = value
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        cat, queue, obs, cap = fixture()
        obs["observations"][0]["source_url"] = "http://localhost:1234/secret"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28")

    def test_reject_duplicate_future_data_wrong_ids_and_nonfinite(self):
        cat, queue, obs, cap = fixture()
        obs["observations"].append(deepcopy(obs["observations"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        cat, queue, obs, cap = fixture()
        obs["observations"][0]["observed_on"] = "2026-11-01"
        with self.assertRaisesRegex(ValueError, "Future"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        cat, queue, obs, cap = fixture()
        obs["observations"][0]["case_id"] = "CASE-99"
        with self.assertRaisesRegex(ValueError, "unknown case"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        cat, queue, obs, cap = fixture()
        obs["observations"][0]["price"]["amount"] = "NaN"
        with self.assertRaisesRegex(ValueError, "bounds"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28")

    def test_manifest_and_previous_snapshot_fail_closed(self):
        cat, queue, obs, cap = fixture()
        del cap["case_needs"]["CASE-12"]
        with self.assertRaisesRegex(ValueError, "every case"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28")
        cat, queue, obs, cap = fixture()
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            evaluate(cat, queue, obs, cap, as_of="2026-10-28", previous={"schema": "wrong"})

    def test_explicit_as_of_and_staleness(self):
        with self.assertRaisesRegex(ValueError, "ISO"):
            self.board(observed_on="now")
        old = self.board(observed_on="2026-12-15")
        self.assertGreater(sum(len(x["stale_observation_ids"]) for x in old["cases"]), 0)
        self.assertTrue(all(not x["qualified_commercial_opportunity"] for x in old["cases"]))

    def test_cli_actual_fixture_and_output_path(self):
        out = StringIO()
        with redirect_stdout(out):
            rc = main(["--as-of", "2026-10-28"])
        self.assertEqual(rc, 0)
        r = json.loads(out.getvalue())
        self.assertEqual(r["summary"]["catalog_concepts"], 64)
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "radar.json"
            rc = main(["--as-of", "2026-10-28", "--output", str(file)])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(file.read_text(encoding="utf-8")), r)


if __name__ == "__main__":
    unittest.main()
