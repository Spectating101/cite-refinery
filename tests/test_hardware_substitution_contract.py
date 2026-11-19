"""Synthetic contract unit tests, not evidence of native CAD/PCB execution.

The byte strings below deliberately are not usable manufacturing files. They
exercise provenance, revision, release-scope and accounting boundaries without
pretending to independently prove electrical or mechanical correctness.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.hardware_substitution import (
    build_manifest,
    derive_material_plan,
    review_fingerprint,
    review_matches,
    validate_board_contract,
    validate_job,
    verify_package,
)


JOB_FIXTURE = Path(__file__).resolve().parents[1] / "examples/hardware_substitution/job.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class HardwareSubstitutionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "package"
        self.pcb = self.root / "pcb"
        self.cad = self.root / "cad"
        self.pcb.mkdir(parents=True)
        self.cad.mkdir(parents=True)
        self.job_path = self.root / "job.json"
        self.engineering_path = self.pcb / "engineering.json"
        self.geometry_path = self.cad / "geometry.json"
        self.board_path = self.pcb / "board.kicad_pcb"
        self.project_path = self.pcb / "board.kicad_pro"
        self.rules_path = self.pcb / "board.kicad_dru"
        self.dsn_path = self.pcb / "board.dsn"
        self.ses_path = self.pcb / "board.ses"
        self.drc_path = self.pcb / "board_drc.json"
        for path in (self.board_path, self.project_path, self.rules_path, self.dsn_path, self.ses_path):
            path.write_bytes(f"CONTRACT UNIT FIXTURE ONLY: {path.name}\n".encode())
        self.job = json.loads(JOB_FIXTURE.read_text(encoding="utf-8"))
        write_json(self.job_path, self.job)
        self.native_drc = {
            "$schema": "https://schemas.kicad.org/drc.v1.json",
            "source": "board.kicad_pcb",
            "kicad_version": "synthetic contract unit fixture",
            "coordinate_units": "mm",
            "violations": [],
            "unconnected_items": [],
            "schematic_parity": [],
        }
        write_json(self.drc_path, self.native_drc)
        recipe = self.job["revision_b"]
        self.engineering = {
            "schema": "cite_refinery.hardware_board.v1",
            "evidence_status": "synthetic contract unit fixture; no engine executed",
            "job_id": self.job["job_id"],
            "revision": "B",
            "board_path": self.board_path.name,
            "board_sha256": digest(self.board_path),
            "source_hashes": {
                "job": digest(self.job_path),
                "project": digest(self.project_path),
                "native_rules": digest(self.rules_path),
                "dsn": digest(self.dsn_path),
                "ses": digest(self.ses_path),
            },
            "bom": [
                {"reference": ref, "part_id": recipe[ref], "quantity_per_board": 1}
                for ref in ("J1", "J2")
            ],
            "connectors": [
                {
                    "reference": ref,
                    "footprint": recipe[ref],
                    "pins": [
                        {"number": number, "net": net}
                        for number, net in self.job["interface"].items()
                    ],
                }
                for ref in ("J1", "J2")
            ],
            "checks": {
                "digital_electrical_pass": True,
                "pin_semantics_match": True,
                "drc": {
                    "report_path": self.drc_path.name,
                    "report_sha256": digest(self.drc_path),
                    "checked_board_sha256": digest(self.board_path),
                    "checked_project_path": self.project_path.name,
                    "checked_project_sha256": digest(self.project_path),
                    "checked_rules_path": self.rules_path.name,
                    "checked_rules_sha256": digest(self.rules_path),
                    "exit_code": 0,
                    "errors": 0,
                    "unconnected": 0,
                    "warnings": 0,
                },
            },
        }
        fabrication = self.pcb / "fabrication"
        fabrication.mkdir()
        self.engineering["manufacturing_artifacts"] = []
        for kind in ("gtl", "gbl", "gts", "gbs", "gto", "gm1", "gbrjob", "drl"):
            path = fabrication / f"board.{kind}"
            path.write_bytes(f"CONTRACT UNIT FIXTURE ONLY: fabrication {kind}\n".encode())
            self.engineering["manufacturing_artifacts"].append({
                "path": path.relative_to(self.pcb).as_posix(),
                "sha256": digest(path),
                "source_board_sha256": digest(self.board_path),
                "format": kind,
            })
        write_json(self.engineering_path, self.engineering)
        self.geometry = {
            "schema": "cite_refinery.hardware_geometry.v1",
            "evidence_status": "synthetic contract unit fixture; no solid imported",
            "job_id": self.job["job_id"],
            "revision": "B",
            "job_sha256": digest(self.job_path),
            "source_board_sha256": digest(self.board_path),
            "source_engineering_sha256": digest(self.engineering_path),
            "physical_release_authorized": False,
            "all_checks_pass": True,
            "variants": [],
        }
        for index, config in enumerate(self.job["configurations"]):
            directory = self.cad / config["id"]
            directory.mkdir()
            files = {}
            for kind in ("base_step", "lid_step", "base_stl", "lid_stl"):
                stem, extension = kind.split("_")
                path = directory / f"{stem}.{extension}"
                path.write_bytes(f"CONTRACT UNIT FIXTURE ONLY: {config['id']} {kind}\n".encode())
                files[kind] = {"path": path.relative_to(self.cad).as_posix(), "sha256": digest(path)}
            self.geometry["variants"].append({
                "configuration_id": config["id"],
                "quantity": config["quantity"],
                "wall_mm": config["wall_mm"],
                "files": files,
                "measurements": {
                    "base_volume_mm3": 6000 + index * 1500,
                    "lid_volume_mm3": 2000 + index * 500,
                    "material_volume_mm3": 8000 + index * 2000,
                    "base_valid_single_solid": True,
                    "lid_valid_single_solid": True,
                    "board_collision_volume_mm3": 0.0,
                    "connector_clearances": [
                        {"reference": ref, "collision_volume_mm3": 0.0, "minimum_clearance_mm": 0.5}
                        for ref in ("J1", "J2")
                    ],
                },
            })
        write_json(self.geometry_path, self.geometry)
        self.manifest = self._manifest()

    def _manifest(self) -> dict:
        return build_manifest(self.root, self.job_path, self.engineering_path, self.geometry_path)

    def _save_engineering(self) -> None:
        write_json(self.engineering_path, self.engineering)
        self.geometry["source_engineering_sha256"] = digest(self.engineering_path)
        write_json(self.geometry_path, self.geometry)

    def _save_job(self) -> None:
        write_json(self.job_path, self.job)
        self.engineering["source_hashes"]["job"] = digest(self.job_path)
        self.geometry["job_sha256"] = digest(self.job_path)
        self._save_engineering()

    def _save_drc(self, raw: dict, exit_code: int = 0) -> None:
        write_json(self.drc_path, raw)
        self.engineering["checks"]["drc"]["report_sha256"] = digest(self.drc_path)
        self.engineering["checks"]["drc"]["exit_code"] = exit_code
        self._save_engineering()

    def test_valid_contract_fixture_remains_digital_only(self) -> None:
        result = verify_package(self.root, self.manifest)
        self.assertTrue(result["digital_package_valid"])
        self.assertEqual(result["revision"], "B")
        self.assertFalse(result["physical_release_authorized"])
        self.assertFalse(result["material_plan"]["commercial_commitment_made"])
        self.assertIsNone(result["previous_review_still_matches"])
        self.assertEqual(result["fingerprint"], review_fingerprint(self.manifest))

    def test_free_stock_is_already_net_of_reservations(self) -> None:
        for reserved in (0, 5, 500):
            with self.subTest(reserved=reserved):
                job = deepcopy(self.job)
                job["supply_fixture"]["reserved_new_connector_stock"] = reserved
                plan = derive_material_plan(job, self.engineering, self.geometry)
                self.assertEqual(plan["demand_by_footprint"], {
                    job["revision_b"]["J1"]: 40,
                    job["revision_b"]["J2"]: 40,
                })
                self.assertEqual(plan["old_connector_shortage"], 0)
                self.assertEqual(plan["free_new_stock_used"], 10)
                self.assertEqual(plan["reserved_new_stock_used"], 0)
                self.assertEqual(plan["reserved_new_stock_preserved"], reserved)
                self.assertEqual(plan["new_connector_shortage"], 30)
                self.assertEqual(plan["purchase_packs"], 3)
                self.assertEqual(plan["purchase_new_units"], 30)
                self.assertEqual(plan["purchase_cost_fixture"], 90)
                self.assertEqual(plan["total_solid_volume_mm3"], 352000)
                self.assertAlmostEqual(plan["estimated_print_hours_fixture"], 14.666667)

    def test_wrong_bom_and_pin_semantics_fail_even_with_pass_flags(self) -> None:
        mutations = {
            "old connector reused": lambda x: x["bom"][0].update(part_id=self.job["revision_a"]["J1"]),
            "doubled quantity": lambda x: x["bom"][0].update(quantity_per_board=2),
            "duplicate reference": lambda x: x["bom"][1].update(reference="J1"),
            "different observed footprint": lambda x: x["connectors"][0].update(footprint="unapproved:part"),
            "wrong pin net": lambda x: x["connectors"][0]["pins"][0].update(net="RETURN"),
            "duplicate pin": lambda x: x["connectors"][0]["pins"][1].update(number="1"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                engineering = deepcopy(self.engineering)
                mutate(engineering)
                with self.assertRaises(ValueError):
                    validate_board_contract(self.job, engineering)

    def test_configuration_totals_and_quantity_types_are_checked(self) -> None:
        mutations = {
            "wrong total": lambda x: x["configurations"][0].update(quantity=25),
            "duplicate id": lambda x: x["configurations"][1].update(id="standard"),
            "boolean quantity": lambda x: x.update(quantity=True),
            "zero wall": lambda x: x["configurations"][0].update(wall_mm=0),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                job = deepcopy(self.job)
                mutate(job)
                with self.assertRaises(ValueError):
                    validate_job(job)

    def test_boolean_and_float_bom_counts_are_not_integer_part_counts(self) -> None:
        for quantity in (True, 1.0, "1"):
            with self.subTest(quantity=quantity, value_type=type(quantity).__name__):
                engineering = deepcopy(self.engineering)
                engineering["bom"][0]["quantity_per_board"] = quantity
                with self.assertRaisesRegex(ValueError, "BOM"):
                    validate_board_contract(self.job, engineering)

    def test_invalid_constraints_cannot_disable_engineering_checks(self) -> None:
        cases = [
            ("mechanical_fixture", "opening_clearance_mm", value)
            for value in (float("nan"), float("inf"), -0.5, 0, True)
        ] + [
            ("board", "width_mm", 0),
            ("board", "thickness_mm", float("nan")),
            ("routing_rules", "minimum_clearance_mm", float("nan")),
            ("routing_rules", "track_width_mm", 0.1),
        ]
        for section, key, value in cases:
            with self.subTest(section=section, key=key, value=value):
                job = deepcopy(self.job)
                job[section][key] = value
                with self.assertRaises(ValueError):
                    validate_job(job)

    def test_missing_fabrication_outputs_fail_build_and_verification(self) -> None:
        complete = deepcopy(self.engineering["manufacturing_artifacts"])
        for missing in ("all", "drl"):
            with self.subTest(missing=missing):
                self.engineering["manufacturing_artifacts"] = (
                    [] if missing == "all" else [item for item in complete if item["format"] != missing]
                )
                self._save_engineering()
                with self.assertRaisesRegex(ValueError, "missing required fabrication"):
                    self._manifest()
                # A caller can bypass the builder. Verification must independently
                # reject freshly hashed receipts with a removed fabrication list.
                manifest = deepcopy(self.manifest)
                manifest["files"]["engineering"]["sha256"] = digest(self.engineering_path)
                manifest["files"]["geometry"]["sha256"] = digest(self.geometry_path)
                retained = {"manufacturing:" + item["path"] for item in self.engineering["manufacturing_artifacts"]}
                for key in list(manifest["files"]):
                    if key.startswith("manufacturing:") and key not in retained:
                        del manifest["files"][key]
                with self.assertRaisesRegex(ValueError, "missing required fabrication"):
                    verify_package(self.root, manifest)

    def test_same_name_byte_tampering_invalidates_saved_manifest(self) -> None:
        paths = (self.board_path, self.project_path, self.rules_path, self.drc_path,
                 self.cad / "standard" / "lid.step")
        for path in paths:
            original = path.read_bytes()
            with self.subTest(artifact=path.name):
                path.write_bytes(original + b"CHANGED UNDER SAME FILE NAME\n")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    verify_package(self.root, self.manifest)
                path.write_bytes(original)

    def test_rebuilt_manifest_cannot_hide_stale_drc_binding(self) -> None:
        self.board_path.write_bytes(b"CONTRACT UNIT FIXTURE: DIFFERENT BOARD SAME REVISION B\n")
        self.engineering["board_sha256"] = digest(self.board_path)
        self.geometry["source_board_sha256"] = digest(self.board_path)
        self._save_engineering()
        with self.assertRaisesRegex(ValueError, "DRC not bound"):
            verify_package(self.root, self._manifest())

    def test_native_rule_changes_require_fresh_engineering_receipt(self) -> None:
        for path in (self.project_path, self.rules_path):
            original = path.read_bytes()
            with self.subTest(artifact=path.name):
                path.write_bytes(original + b"CHANGED DRC INPUT\n")
                with self.assertRaisesRegex(ValueError, "project|rule|DRC"):
                    verify_package(self.root, self._manifest())
                path.write_bytes(original)

    def test_mixed_revision_case_is_rejected(self) -> None:
        self.geometry["revision"] = "A"
        write_json(self.geometry_path, self.geometry)
        with self.assertRaisesRegex(ValueError, "mixed revisions"):
            verify_package(self.root, self._manifest())

    def test_old_case_relabelled_b_still_has_wrong_source_board(self) -> None:
        self.geometry["revision"] = "B"
        self.geometry["source_board_sha256"] = hashlib.sha256(b"OLD BOARD A").hexdigest()
        write_json(self.geometry_path, self.geometry)
        with self.assertRaisesRegex(ValueError, "geometry receipt belongs to different"):
            verify_package(self.root, self._manifest())

    def test_old_case_file_hash_cannot_be_replaced_by_manifest_alone(self) -> None:
        path = self.cad / "standard" / "lid.step"
        path.write_bytes(b"CONTRACT UNIT FIXTURE: STALE CASE A\n")
        with self.assertRaisesRegex(ValueError, "geometry artifact is stale"):
            verify_package(self.root, self._manifest())

    def test_missing_and_malformed_native_drc_are_not_zero_errors(self) -> None:
        missing = deepcopy(self.manifest)
        del missing["files"]["drc"]
        with self.assertRaisesRegex(ValueError, "missing required"):
            verify_package(self.root, missing)
        for raw in ({}, {"violations": []}, {"violations": [], "unconnected_items": {}}):
            with self.subTest(raw=raw):
                self._save_drc(raw)
                with self.assertRaisesRegex(ValueError, "native DRC result arrays"):
                    verify_package(self.root, self._manifest())
        self.drc_path.write_text("{ malformed JSON", encoding="utf-8")
        self.engineering["checks"]["drc"]["report_sha256"] = digest(self.drc_path)
        self._save_engineering()
        with self.assertRaises(ValueError):
            verify_package(self.root, self._manifest())

    def test_native_failures_override_claimed_electrical_pass(self) -> None:
        cases = (
            ({"violations": [{"severity": "error", "description": "fixture clearance failure"}],
              "unconnected_items": []}, 0),
            ({"violations": [], "unconnected_items": [{"description": "fixture open net"}]}, 0),
            ({"violations": [], "unconnected_items": []}, 2),
        )
        for raw, exit_code in cases:
            with self.subTest(raw=raw, exit_code=exit_code):
                self._save_drc(raw, exit_code)
                with self.assertRaisesRegex(ValueError, "native DRC errors"):
                    verify_package(self.root, self._manifest())

    def test_collisions_and_clearance_override_claimed_mechanical_pass(self) -> None:
        measurements = deepcopy(self.geometry["variants"][0]["measurements"])
        mutations = {
            "invalid solid": lambda x: x.update(lid_valid_single_solid=False),
            "board collision": lambda x: x.update(board_collision_volume_mm3=1.0),
            "connector collision": lambda x: x["connector_clearances"][0].update(collision_volume_mm3=1.0),
            "insufficient clearance": lambda x: x["connector_clearances"][0].update(minimum_clearance_mm=0.1),
            "missing connector check": lambda x: x["connector_clearances"].pop(),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                changed = deepcopy(measurements)
                mutate(changed)
                self.geometry["variants"][0]["measurements"] = changed
                write_json(self.geometry_path, self.geometry)
                with self.assertRaises(ValueError):
                    verify_package(self.root, self._manifest())

    def test_geometry_quantities_and_required_files_cannot_silently_disappear(self) -> None:
        self.geometry["variants"][0]["quantity"] = 23
        write_json(self.geometry_path, self.geometry)
        with self.assertRaisesRegex(ValueError, "geometry quantity differs"):
            verify_package(self.root, self._manifest())
        self.geometry["variants"][0]["quantity"] = 24
        del self.geometry["variants"][0]["files"]["lid_step"]
        write_json(self.geometry_path, self.geometry)
        with self.assertRaisesRegex(ValueError, "missing enclosure manufacturing"):
            verify_package(self.root, self._manifest())

    def test_no_layer_can_assert_physical_release(self) -> None:
        manifest = deepcopy(self.manifest)
        manifest["physical_release_authorized"] = True
        with self.assertRaisesRegex(ValueError, "physical-release"):
            verify_package(self.root, manifest)
        job = deepcopy(self.job)
        job["release_policy"]["physical_release_authorized"] = True
        with self.assertRaisesRegex(ValueError, "physical release"):
            validate_job(job)
        self.geometry["physical_release_authorized"] = True
        write_json(self.geometry_path, self.geometry)
        with self.assertRaisesRegex(ValueError, "overclaimed"):
            verify_package(self.root, self._manifest())

    def test_review_fingerprint_changes_with_revised_job_despite_same_revision(self) -> None:
        previous = review_fingerprint(self.manifest)
        unchanged = verify_package(self.root, self.manifest, previous_review_fingerprint=previous)
        self.assertTrue(unchanged["previous_review_still_matches"])
        self.job["supply_fixture"]["candidate_supplier_unit_price"] = 4.0
        self._save_job()
        changed = self._manifest()
        self.assertFalse(review_matches(changed, previous))
        result = verify_package(self.root, changed, previous_review_fingerprint=previous)
        self.assertTrue(result["digital_package_valid"])
        self.assertFalse(result["previous_review_still_matches"])
        self.assertFalse(result["physical_release_authorized"])
        self.assertEqual(result["material_plan"]["purchase_cost_fixture"], 120)

    def test_external_current_job_change_invalidates_old_package(self) -> None:
        revised_job = self.root / "current_job.json"
        job = deepcopy(self.job)
        job["configurations"][0]["wall_mm"] = 2.5
        write_json(revised_job, job)
        with self.assertRaisesRegex(ValueError, "job changed after engineering checks"):
            verify_package(self.root, self.manifest, current_job_path=revised_job)

    def test_absolute_parent_traversal_and_symlink_escape_are_rejected(self) -> None:
        outside = Path(self.temporary.name) / "outside.kicad_pcb"
        outside.write_bytes(self.board_path.read_bytes())
        symlink = self.root / "escape.kicad_pcb"
        symlink.symlink_to(outside)
        for path in (str(outside), "../outside.kicad_pcb", "escape.kicad_pcb"):
            with self.subTest(path=path):
                manifest = deepcopy(self.manifest)
                manifest["files"]["board"] = {"path": path, "sha256": digest(outside)}
                with self.assertRaisesRegex(ValueError, "relative|outside package"):
                    verify_package(self.root, manifest)


if __name__ == "__main__":
    unittest.main()
