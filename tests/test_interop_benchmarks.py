"""Offline contract tests for experimental external interoperability benchmarks.

CI does not download upstream packages, access private repositories,
start a web server, or depend on bench-only third-party engines.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InteropRunnerTests(unittest.TestCase):
    def test_original_cell_representation_is_not_coerced(self):
        pdf=load("interop_pdf_benchmark")
        payload=pdf.canonical_tables([
            [["Material","Unit price ($)"],["Cedar mulch","64.00"],["Gravel","064.00"]],
            [[None,"-0.08"],["Another","12,500"]],
        ])
        self.assertEqual(payload["tables"][0][1][1], "64.00")
        self.assertEqual(payload["tables"][0][2][1], "064.00")
        self.assertEqual(payload["tables"][1][0], ["","-0.08"])
        self.assertNotEqual(payload["tables"][0][2][1],payload["tables"][0][1][1])

    def test_nan_empty_table_cells_do_not_make_the_entire_table_fail(self):
        pdf=load("interop_pdf_benchmark")
        out=pdf.canonical_tables([[["Material","Volume","Unit price"],
                                   ["Cedar mulch",float("nan"),"64.00"]]])
        self.assertEqual(out["tables"][0][1],["Cedar mulch","","64.00"])

    def test_numeric_input_rejected_instead_of_silent_normalization(self):
        pdf=load("interop_pdf_benchmark")
        with self.assertRaises(ValueError):
            pdf.canonical_tables([[["Material","Price"],["Cedar",64.0]]])

    def test_empty_or_invalid_table_not_silently_success(self):
        pdf=load("interop_pdf_benchmark")
        self.assertEqual(pdf.canonical_tables([]), {"tables":[]})
        with self.assertRaises(TypeError):
            pdf.canonical_tables([["not a row"]])
        with self.assertRaises(ValueError):
            pdf.extraction(Path("/dev/null"),"unknown_engine")

    def test_invalid_fixture_root_is_rejected_without_side_effect(self):
        pdf=load("interop_pdf_benchmark")
        with tempfile.TemporaryDirectory() as t:
            dest=Path(t)/"no_output"
            with self.assertRaises(ValueError):
                pdf.run(Path(t),dest)
            self.assertFalse(dest.exists())

    def test_nocturnal_runner_refuses_nonrepo(self):
        warc=load("interop_warc_benchmark")
        with tempfile.TemporaryDirectory() as t:
            dest=Path(t)/"out"
            with self.assertRaises(ValueError):
                warc.run(Path(t),dest)
            self.assertFalse(dest.exists())

    def test_checked_in_execution_receipt_is_bounded_and_consistent(self):
        doc=json.loads((ROOT/"examples/discovery/interop_benchmark_results_20261102.json").read_text())
        self.assertEqual(doc["schema"],"cite_refinery.external_interoperability_receipt.v1")
        cases=doc["pdf"]["results"]
        self.assertEqual(len(cases),18)
        self.assertEqual(len({c["engine"] for c in cases}),6)
        self.assertEqual(len({c["case"] for c in cases}),3)
        best=[c for c in cases if c["engine"]=="img2table_borderless"]
        self.assertEqual(sum(c["checks"]["pass"] for c in best),9)
        self.assertEqual(sum(c["checks"]["fail"] for c in best),0)
        self.assertEqual(sum(c["checks"]["unknown"] for c in best),0)
        self.assertFalse(doc["pdf"]["actual_native_query"]["ok"])
        self.assertEqual(doc["pdf"]["actual_native_query"]["error"],"metadata_only_backend")
        self.assertTrue(doc["nocturnal"]["pywb_offline_replay_success"])
        self.assertEqual(doc["nocturnal"]["replay_sha256"],doc["nocturnal"]["native_html_sha256"])
        self.assertNotIn("/home/phyrexian/",json.dumps(doc))

    def test_warc_probe_uses_unresolvable_public_fixture_and_no_live_download(self):
        warc=load("interop_warc_benchmark")
        self.assertTrue(warc.SOURCE.startswith("http://example.invalid/"))
        self.assertIn("Original evidence claim",warc.HTML)
        self.assertEqual(warc.SCHEMA,"cite_refinery.nocturnal_warc_interop.v1")


if __name__ == "__main__":
    unittest.main()
