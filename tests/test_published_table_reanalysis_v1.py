"""Publication-table replication and source-data quality checks, fully offline."""
from __future__ import annotations
import csv
import json
import unittest
from pathlib import Path

from scripts.summarize_published_table_replication import assess_replication

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/"research_materials/runtime_trials/fulltext_dog_20261020"

def read(name):
    return json.loads((DATA/name).read_text(encoding="utf-8"))


class PublishedTable2Tests(unittest.TestCase):
    def setUp(self):
        self.quality=read("published_program_table_quality.json")
        self.models=read("table2_nb_sensitivity.json")

    def test_published_program_count_and_effort(self):
        with (DATA/"table2_programs_from_publication.csv").open(newline="") as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),80)
        self.assertEqual(sum(int(x["Days"])>0 for x in rows),68)
        self.assertEqual(sum(int(x["Days"])==0 for x in rows),12)
        self.assertEqual(self.quality["source_subtotals_checked"],20)
        self.assertEqual(self.quality["row_count"],80)
        self.assertTrue(all(int(x["Days"])>0 or int(x["Total"])==0 for x in rows))

    def test_specific_source_arithmetic_mismatches_not_silently_repaired(self):
        with (DATA/"table2_programs_from_publication.csv").open(newline="") as f:
            lookup={(x["Year"],x["Zone"],x["Program"]):x for x in csv.DictReader(f)}
        a=lookup["2023","3","2"]
        b=lookup["2024","3","1"]
        self.assertEqual([int(a[x]) for x in ["Total","Male","Female"]],[62,11,47])
        self.assertEqual([int(b[x]) for x in ["Total","Male","Female"]],[120,49,87])
        mismatch=[x for x in self.quality["arithmetic_issues"]
                  if x["type"]=="within_row_sex_total_mismatch"]
        self.assertEqual(len(mismatch),2)
        self.assertEqual({x["difference_total_minus_sex_sum"] for x in mismatch},{4,-16})
        blank=[x for x in self.quality["arithmetic_issues"]
               if x["type"]=="unlabelled_printed_subtotal"]
        self.assertEqual(len(blank),1)
        self.assertEqual((blank[0]["year"],blank[0]["zone"]),("2023","1"))

    def test_audit_has_twelve_prefixed_fits_and_preserves_original_comparison(self):
        report=assess_replication(self.quality,self.models)
        self.assertEqual(report["models_total"],12)
        self.assertEqual(report["positive_effort_rows"],68)
        self.assertEqual(report["zero_day_rows_excluded_in_log_offset"],12)
        self.assertEqual(report["close_IRR_and_p_reproductions_at_preregistered_tolerances"],0)
        self.assertEqual(len(report["within_row_sex_total_mismatches"]),2)
        self.assertGreaterEqual(report["very_high_or_nonfinite_theta_fits"],1)
        keys={(m["granularity"],m["region"],m["outcome"]) for m in report["model_sensitivity_cases"]}
        self.assertEqual(len(keys),12)
        allprog=next(x for x in report["model_sensitivity_cases"] if
                     x["granularity"]=="program_records" and
                     x["region"]=="inner_plus_buffer" and x["outcome"]=="Total")
        self.assertAlmostEqual(allprog["IRR"],1.0378,delta=0.001)
        self.assertGreater(allprog["p_value"],0.2)
        self.assertLess(allprog["p_value"],0.25)

    def test_audit_rejects_incompatible_source_or_model_schema(self):
        source=dict(self.quality,table_id="T15")
        with self.assertRaises(ValueError):assess_replication(source,self.models)
        outcomes=dict(self.models,schema="unverified")
        with self.assertRaises(ValueError):assess_replication(self.quality,outcomes)

    def test_boundaries_dont_claim_exact_reproduction(self):
        report=assess_replication(self.quality,self.models)
        text=json.dumps(report["claim_scope"])
        self.assertIn("missing",text)
        self.assertIn("not_exact",report["authority"])
        self.assertIn("analysis scripts",text)


if __name__=="__main__":unittest.main()
