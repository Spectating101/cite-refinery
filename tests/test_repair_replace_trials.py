"""Source-pinned replacement assessment does not imply deployment or revenue."""
import json
from pathlib import Path
import tempfile
import unittest
from cite_refinery.repair_replace_trials import PINS,replace_one,repo,markdown
DATA=Path(__file__).resolve().parents[1]/"research_materials/opportunity_atlas"
def read(name):return json.loads((DATA/name).read_text(encoding="utf-8"))
class RepairReplaceTest(unittest.TestCase):
    def test_repairs_are_scoped_and_executed(self):
        doc=read("repair_replace_executable_results.json")
        self.assertEqual(doc["schema"],"cite_refinery.repair_replace_executable_review.v1")
        self.assertEqual(doc["source_pins"],PINS)
        b,f,c=doc["domains"]
        self.assertEqual(len(b["route_trials"]),3)
        self.assertTrue(b["local_repair_synthetic_pass"])
        self.assertFalse(b["repair_modifies_upstream"])
        for row in b["route_trials"]:
            self.assertTrue(row["passed"])
            self.assertEqual(row["original_paid_fee_profit_delta_usd"],0)
            self.assertEqual(row["local_repair_paid_fee_profit_delta_usd"],-10_000_000)
            self.assertEqual(row["local_repair_cost_increase_usd"],10_000_000)
            self.assertEqual(row["negative_fee_income_preserved_usd"],20_000_000)
        self.assertTrue(f["local_repair_synthetic_pass"])
        self.assertFalse(f["repair_modifies_upstream"])
        self.assertEqual(len(f["input_ordering_trials"]),6)
        self.assertTrue(f["invalid_level_returned_none"])
        self.assertTrue(all(x["pass"] and x["top_one"]==["high"] for x in f["input_ordering_trials"]))
    def test_alternatives_are_not_drop_in(self):
        b,f,c=read("repair_replace_executable_results.json")["domains"]
        self.assertTrue(b["alternative_economics_module_empty"])
        self.assertFalse(b["alternative_root_license_detected"])
        self.assertFalse(b["alternative_gate_fee_model_executed"])
        self.assertFalse(b["operational_profit_established"])
        self.assertFalse(f["equivalent_replacement_verified"])
        self.assertFalse(f["real_warning_performance_verified"])
        self.assertFalse(c["original_yaml_valid"])
        self.assertEqual(len(c["config_alternative_checks"]),2)
        self.assertTrue(all(x["yaml_parsed_with_supported_secret_tag"] and
                            x["missing_fonts"] and not x["esphome_compiled"]
                            for x in c["config_alternative_checks"]))
        self.assertFalse(c["config_alternative_license_file_detected"])
        self.assertFalse(c["config_alternative_drop_in_for_scd30"])
        self.assertTrue(c["mit_license_detected"])
        self.assertTrue(c["scd30_driver_source_present"])
        self.assertFalse(c["other_architecture_is_esphome_yaml"])
        self.assertFalse(c["firmware_compiled"])
        self.assertFalse(c["sensor_accuracy_verified"])
    def test_no_authority_promotion(self):
        data=read("repair_replace_executable_results.json")
        self.assertFalse(data["outcomes"]["verified_drop_in_replacement"])
        self.assertFalse(data["outcomes"]["commercial_value_or_real_world_effect_verified"])
        self.assertFalse(data["outcomes"]["native_graph_promoted"])
        self.assertIn("No full operational integration",markdown(data))
    def test_pinned_repo_and_exact_edit_guards(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"clone missing"):
                repo(Path(td),"Jamie-Hough__Batteryloop")
        with self.assertRaisesRegex(ValueError,"unknown inspected"):
            repo(Path("/tmp"),"fictional-project")
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            replace_one("one two","absent","replacement")
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            replace_one("word word","word","fixed")
