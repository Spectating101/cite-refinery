"""Offline contract + synthetic negative tests for expanded interoperability.

No benchmark package downloads, Nocturnal import, or real website fetch in CI.
"""
import importlib.util
import json
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


def load(script):
    if str(ROOT/"scripts") not in sys.path: sys.path.insert(0,str(ROOT/"scripts"))
    spec=importlib.util.spec_from_file_location(script,ROOT/"scripts"/(script+".py"))
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ExpandedAcceptanceTests(unittest.TestCase):
    def test_single_header_naive_drops_rows_at_page_starts(self):
        m=load("interop_multipage_benchmark")
        header=["Item","Zone","Count","Price"]
        pages=[[[header,["Plant-01","Z2","21","1.50"]]],
               [[["Plant-09","Z1","29","10.25"],["Plant-10","Z2","30","11.25"]]],
               [[["Plant-17","Z3","37","18.25"]]]]
        naive=m.verify(pages,carry_forward=False)
        self.assertIn("Plant-09",naive["missing"])
        self.assertIn("Plant-17",naive["missing"])
        assist=m.verify(pages,carry_forward=True)
        self.assertNotIn("Plant-09",assist["missing"])
        self.assertNotIn("Plant-17",assist["missing"])
        self.assertFalse(assist["complete"])  # Other 20 absent!

    def test_explicit_header_does_not_produce_phantom_row(self):
        m=load("interop_multipage_benchmark")
        header=["Item","Zone","Count","Price"]
        pages=[[[header,["Plant-01","Z2","21","1.50"]]],
               [[header,["Plant-09","Z1","29","10.25"]]]]
        result=m.verify(pages,carry_forward=True)
        self.assertEqual(result["details"][1]["status"],"EXPLICIT_SOURCE_HEADER")
        self.assertEqual(result["pass"],2)

    def test_ambiguous_shape_abstains_from_row_assignment(self):
        m=load("interop_multipage_benchmark")
        result=m.verify([[[["Plant-01","21"]]]],carry_forward=True)
        self.assertEqual(result["details"][0]["status"],"UNKNOWN_COLUMN_SHAPE")
        self.assertEqual(result["pass"],0)
        self.assertFalse(result["complete"])

    def test_summary_has_negative_controls_and_no_false_auto_adoption(self):
        d=json.loads((ROOT/"examples/discovery/interop_acceptance_002_20261103.json").read_text())
        self.assertEqual(d["schema"],"cite_refinery.real_interop_acceptance_002.v1")
        naive=[r for r in d["multipage"] if r["case"]=="single-header" and r["mode"]=="naive_page_header"]
        self.assertEqual(len(naive),3)
        self.assertTrue(all(r["correct_row_count"]==22 and
                            r["missing_row_ids"]==["Plant-09","Plant-17"] and
                            r["pass"] is False for r in naive))
        aided=[r for r in d["multipage"] if r["case"]=="single-header" and r["mode"]=="operator_declared_header"]
        self.assertTrue(all(r["correct_row_count"]==24 and r["pass"] is True for r in aided))
        position=d["positioned"]
        self.assertEqual(len(position),4)
        self.assertTrue(all(r["status"]=="unknown" for r in position if not r["operator_defined_scope"]))
        self.assertEqual([r["status"] for r in position if r["operator_defined_scope"]],["pass"])
        self.assertTrue(all(r["decision"]!="AUTO_ADOPT" for r in d["project_decisions"]))
        self.assertEqual(d["nocturnal"]["repair_pr"],
                         "https://github.com/Spectating101/nocturnal-oversight/pull/114")

    def test_expanded_bench_scripts_refuse_non_repo_fixture(self):
        a=load("interop_multipage_benchmark")
        b=load("interop_positional_benchmark")
        self.assertEqual(len(a.ENGINE_NAMES),3)
        self.assertEqual(len(b.ENGINES),4)
        self.assertEqual(a.FIXTURE_COMMIT,b.PINNED_FIXTURE_COMMIT)


if __name__=="__main__":
    unittest.main()
