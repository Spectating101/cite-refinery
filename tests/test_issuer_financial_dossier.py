"""Financial research output must be source-backed and guard against overclaim."""
import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from scripts.issuer_financial_dossier import validate_snapshot,render_markdown,percentage

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"examples/discovery/manulife_1q24_vs_1q23_decision_dossier_20261105.json"
MD=ROOT/"reports/manulife_1q24_vs_1q23_decision_brief_20261105.md"
HTML=ROOT/"reports/manulife_1q24_vs_1q23_decision_brief_20261105.html"


class IssuerFinancialDecisionProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=json.loads(DATA.read_text())

    def test_all_primary_original_source_rows_and_history(self):
        a=self.d
        self.assertTrue(validate_snapshot(a))
        self.assertEqual(a["schema"],"atlas.issuer_financial_decision_dossier.v1")
        self.assertEqual(a["issuer_2024_rows_verified_shareholder"],8)
        self.assertEqual(a["issuer_2024_rows_verified_release"],7)
        self.assertEqual(a["issuer_2024_expense_qualifier_verified"],1)
        self.assertEqual(a["historical_rows_with_two_same_issuer_exhibits"],7)
        self.assertEqual(a["historical_expense_rows_one_exhibit"],3)
        self.assertEqual(len(a["metrics"]),10)
        self.assertTrue(a["secondary_pdf_sha_rechecked"])
        self.assertEqual((a["secondary_parser_prior_strict_matches"],
                          a["secondary_parser_prior_abstentions"]),(6,2))
        self.assertFalse(a["auto_publish"])
        self.assertEqual(a["independent_human_approvals"],0)
        self.assertEqual(a["trusted_dataset_promotions"],0)
        self.assertFalse(a["source_exhibits"]["shareholder_report"]["earlier_capture_same_bytes"])
        self.assertFalse(a["source_exhibits"]["earnings_release"]["earlier_capture_same_bytes"])

    def test_original_numbers_and_gap_reproducible(self):
        row={x["id"]:x for x in self.d["metrics"]}
        amounts={
            "manulife-01":("866","1406"),"manulife-02":("1754","1531"),
            "manulife-04":("1883","1600"),"manulife-06":("658","442"),
            "manulife-05":("669","509"),"manulife-07":("6.7","4.4"),
            "manulife-08":("880","804"),"general_expenses":("1102","1086"),
            "total_expenses":("1679","1665"),"core_expenses":("1673","1605")
        }
        for name,(current,prior) in amounts.items():
            self.assertEqual((row[name]["now"],row[name]["prior"]),(current,prior))
            self.assertEqual(Decimal(row[name]["computed_nominal_change_pct"]),
                percentage(Decimal(current),Decimal(prior)))
        self.assertEqual(self.d["analysis"]["gap_core_minus_net_2024_cad_millions"],"888")
        self.assertEqual(self.d["analysis"]["gap_core_minus_net_2023_cad_millions"],"125")
        self.assertEqual(row["manulife-04"]["issuer_printed_change"],"21%")
        self.assertEqual(row["manulife-02"]["issuer_printed_change"],"16%")
        self.assertLess(Decimal(row["manulife-04"]["computed_nominal_change_pct"]),Decimal("21"))
        self.assertEqual((row["total_expenses"]["source_cells"][0]["table"],
                          row["total_expenses"]["source_cells"][0]["col_2023"]),(329,19))

    def test_static_product_is_consistent_with_structured_evidence(self):
        md=MD.read_text()
        html=HTML.read_text()
        self.assertEqual(md,render_markdown(self.d))
        self.assertIn("C\\$125m to C\\$888m",md)
        self.assertIn("C$125m to C$888m",html)
        self.assertIn("Net income",md)
        self.assertIn("APE sales",md)
        self.assertIn("C$m",html)
        self.assertIn("Q1 2024",html)
        self.assertIn("0",str(self.d["trusted_dataset_promotions"]))
        self.assertEqual(html.count("<h1"),1)
        self.assertIn("https://www.sec.gov/Archives/edgar/data/1086888/",html)
        self.assertEqual(html.count("<tr"),11)  # 10 source rows + header

    def test_perturbed_denominators_and_issuer_custody_cannot_render(self):
        base=self.d
        modified=copy.deepcopy(base)
        modified["metrics"][0]["prior"]="1405"
        with self.assertRaisesRegex(ValueError,"nominal comparison"):
            validate_snapshot(modified)
        modified=copy.deepcopy(base)
        modified["analysis"]["gap_core_minus_net_2024_cad_millions"]="889"
        with self.assertRaisesRegex(ValueError,"core versus net"):
            validate_snapshot(modified)
        modified=copy.deepcopy(base)
        modified["trusted_dataset_promotions"]=1
        with self.assertRaisesRegex(ValueError,"trust or original"):
            validate_snapshot(modified)
        modified=copy.deepcopy(base)
        modified["metrics"][0]["source_cells"].pop()
        with self.assertRaisesRegex(ValueError,"coverage"):
            validate_snapshot(modified)
        modified=copy.deepcopy(base)
        modified["source_exhibits"]["earnings_release"]["url"]="https://example.org/fake.html"
        with self.assertRaisesRegex(ValueError,"custody"):
            validate_snapshot(modified)


if __name__=="__main__":
    unittest.main()
