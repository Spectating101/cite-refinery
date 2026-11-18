"""Portable candidate custody and scope checks; not legal accuracy estimates."""
import base64
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.legal_codex_nocturnal_handoff import (
    BOUNDARIES, build_handoff, canonical_bytes, digest, packet_digest,
    read_packet, validate_handoff,
)


def reseal(packet):
    packet["packet_sha256"] = packet_digest(packet)
    packet["packet_id"] = "legal-codex-021-" + packet["packet_sha256"][:24]
    return packet


class PacketJSON021Tests(unittest.TestCase):
    def test_duplicate_keys_are_not_silently_accepted(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "packet.json"
            path.write_text('{"schema":"first","schema":"second"}')
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                read_packet(path)

    def test_nonfinite_values_are_not_portable_json(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "packet.json"
            path.write_text('{"value":NaN}')
            with self.assertRaisesRegex(ValueError, "nonfinite"):
                read_packet(path)


@unittest.skipUnless(os.environ.get("LEGAL_CODEX_020_DUTCH") and os.environ.get("LEGAL_CODEX_020_FINLEX"),
                     "Actual pinned Dutch and Finnish sources required")
class RealNocturnalHandoff021Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger_path = Path(__file__).resolve().parents[1] / "examples/legal_codex_remedy_020.json"
        cls.dutch = os.environ["LEGAL_CODEX_020_DUTCH"]
        cls.finlex = os.environ["LEGAL_CODEX_020_FINLEX"]
        captured = [row["attempted_at"][:10] for row in json.loads(
            (Path(cls.dutch) / "receipt.json").read_text())["sources"]]
        captured.append(json.loads((Path(cls.finlex) / "receipt.json").read_text())["attempted_at"][:10])
        cls.as_of = max(captured)
        cls.original = build_handoff(cls.dutch, cls.finlex, cls.ledger_path, cls.as_of)

    def setUp(self):
        self.packet = deepcopy(self.original)

    def test_actual_packet_roundtrips_without_cite_report_input(self):
        result = validate_handoff(self.packet, expected_packet_sha256=self.original["packet_sha256"])
        self.assertEqual(result, self.original)
        self.assertEqual(result["counts"], {"sources": 4, "components": 12, "events": 27,
                                         "components_confirmed_by_public_source": 3})
        self.assertEqual(result["boundaries"], BOUNDARIES)

    def test_exact_public_source_bodies_and_anchors_survive_portable_json(self):
        restored = json.loads(json.dumps(self.packet, ensure_ascii=False))
        for source in restored["sources"]:
            raw = base64.b64decode(source["raw_content_base64"], validate=True)
            self.assertEqual(digest(raw), source["raw_sha256"])
            self.assertEqual(len(raw), source["raw_bytes"])
            self.assertEqual(source["captured_at"], source["capture_receipt"]["attempted_at"])
            self.assertFalse(source["historical_version_verified"])
        sources = {source["source_id"]: source for source in restored["sources"]}
        for event in restored["events"]:
            blocks = {block["id"]: block for block in sources[event["source_id"]]["extracted_document"]["blocks"]}
            block = blocks[event["block_id"]]
            self.assertEqual(event["source_quote"], block["text"])
            self.assertEqual(event["block_sha256"], block["sha256"])
        self.assertEqual(validate_handoff(restored), self.original)

    def test_order_receipt_fulfillment_and_remedial_decision_remain_separate(self):
        rows = {row["id"]: row for row in self.packet["components"]}
        self.assertEqual(rows["h26_log_explanation"]["disposition"], "ordered")
        self.assertEqual(rows["h26_log_explanation"]["delivery"], "receipt_reported")
        self.assertEqual(rows["h26_log_explanation"]["fulfillment"], "unverified")
        self.assertEqual(rows["h26_log_explanation"]["pre_order_receipt_ids"], ["h26_prior_logs"])
        self.assertTrue(rows["ministry_delivery"]["remedial_decision_reported"])
        self.assertEqual(rows["ministry_delivery"]["delivery"], "unverified")
        self.assertEqual(rows["ministry_employee_names"]["disposition"], "requirement_reversed")
        self.assertEqual(rows["finland_older_logs"]["disposition"], "further_order_not_issued")
        self.assertEqual(rows["finland_older_logs"]["fulfillment"], "nonfulfillment_confirmed_by_public_source")

    def test_nonfinality_disputed_intervals_and_date_bases_remain_explicit(self):
        source = next(row for row in self.packet["sources"] if row["source_id"] == "finnish_tax_2026")
        self.assertEqual(source["decision_finality"], "not_final_as_published")
        self.assertEqual(source["source_date"], "2026-10-23")
        self.assertEqual(source["extracted_document"]["metadata"]["produced_dates"], ["2026-11-10"])
        self.assertEqual(source["availability_basis"], "first_verified_capture")
        self.assertIn("not a complete text edition", source["extraction_scope"])
        flags = " ".join(flag for row in self.packet["components"] for flag in row["data_quality_flags"])
        for value in ("31 December 2021", "28 November 2021", "13 April 2019", "13 May 2019"):
            self.assertIn(value, flags)

    def test_changed_public_xml_is_rejected_even_with_recomputed_envelope_hashes(self):
        source = self.packet["sources"][0]
        raw = base64.b64decode(source["raw_content_base64"]) + b"\n"
        source.update(raw_content_base64=base64.b64encode(raw).decode(), raw_sha256=digest(raw), raw_bytes=len(raw))
        source["capture_receipt"].update(raw_sha256=digest(raw), raw_bytes=len(raw))
        source["capture_receipt_sha256"] = digest(canonical_bytes(source["capture_receipt"]))
        with self.assertRaises(ValueError):
            validate_handoff(reseal(self.packet))

    def test_rehashed_extracted_text_cannot_replace_raw_source_text(self):
        source = self.packet["sources"][0]
        block = source["extracted_document"]["blocks"][0]
        block["text"] = "False assertion that the order was fully performed."
        block["sha256"] = digest(block["text"].encode())
        source["extracted_sha256"] = digest(canonical_bytes(source["extracted_document"]))
        with self.assertRaisesRegex(ValueError, "re-extraction"):
            validate_handoff(reseal(self.packet))

    def test_rehashed_event_quote_must_still_match_the_ledger_anchor(self):
        self.packet["events"][0]["source_quote"] = "False exact quotation."
        self.packet["events"][0]["block_sha256"] = digest(b"False exact quotation.")
        with self.assertRaisesRegex(ValueError, "recomputation"):
            validate_handoff(reseal(self.packet))

    def test_wrong_case_component_binding_is_rejected(self):
        event = next(row for row in self.packet["input_ledger"]["events"] if row["id"] == "h26_prior_logs")
        event["obligation_id"] = "h24_log_overviews"
        self.packet["input_ledger_sha256"] = digest(canonical_bytes(self.packet["input_ledger"]))
        with self.assertRaisesRegex(ValueError, "different proceeding"):
            validate_handoff(reseal(self.packet))

    def test_reported_receipt_cannot_be_promoted_to_order_fulfillment_in_projection(self):
        row = next(row for row in self.packet["components"] if row["id"] == "h26_log_explanation")
        row["fulfillment"] = "confirmed_by_public_source"
        with self.assertRaisesRegex(ValueError, "recomputation"):
            validate_handoff(reseal(self.packet))

    def test_nonfinal_status_cannot_be_relabelled_final(self):
        source = next(row for row in self.packet["sources"] if row["source_id"] == "finnish_tax_2026")
        source["decision_finality"] = "final"
        with self.assertRaisesRegex(ValueError, "recomputation"):
            validate_handoff(reseal(self.packet))

    def test_component_discrepancy_flags_cannot_be_removed_from_projection(self):
        row = next(row for row in self.packet["components"] if row["id"] == "finland_later_logs")
        self.assertTrue(row["data_quality_flags"])
        row["data_quality_flags"] = []
        with self.assertRaisesRegex(ValueError, "recomputation"):
            validate_handoff(reseal(self.packet))

    def test_capture_receipt_cannot_claim_unobserved_source_identity(self):
        source = self.packet["sources"][0]
        source["capture_receipt"]["identity"] = "ANOTHER-CASE"
        source["capture_receipt_sha256"] = digest(canonical_bytes(source["capture_receipt"]))
        with self.assertRaisesRegex(ValueError, "custody"):
            validate_handoff(reseal(self.packet))

    def test_intervention_and_publication_authority_are_not_exportable(self):
        for field, value in (("intervention_verdict", {"effective": True}), ("publication_authorized", True),
                             ("original_claimant_record_custody", True)):
            with self.subTest(field=field):
                packet = deepcopy(self.original)
                packet["boundaries"][field] = value
                with self.assertRaisesRegex(ValueError, "boundaries"):
                    validate_handoff(reseal(packet))

    def test_duplicate_sources_and_missing_events_are_rejected(self):
        self.packet["sources"].append(deepcopy(self.packet["sources"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate source"):
            validate_handoff(reseal(self.packet))
        self.packet = deepcopy(self.original)
        self.packet["events"].pop()
        with self.assertRaisesRegex(ValueError, "recomputation"):
            validate_handoff(reseal(self.packet))

    def test_selected_packet_digest_blocks_a_different_candidate_version(self):
        self.packet["input_ledger"]["description"] += " Analyst revision."
        self.packet["input_ledger_sha256"] = digest(canonical_bytes(self.packet["input_ledger"]))
        with self.assertRaisesRegex(ValueError, "expected digest"):
            validate_handoff(reseal(self.packet), expected_packet_sha256=self.original["packet_sha256"])

    def test_no_intake_of_future_evidence_at_an_earlier_cutoff(self):
        with self.assertRaisesRegex(ValueError, "no publicly visible"):
            build_handoff(self.dutch, self.finlex, self.ledger_path, "2026-11-01")
        self.packet["as_of"] = "2026-11-01"
        with self.assertRaisesRegex(ValueError, "visible events"):
            validate_handoff(reseal(self.packet))

    def test_source_inputs_are_validated_before_building(self):
        import shutil
        with TemporaryDirectory() as folder:
            dest = Path(folder) / "dutch"
            shutil.copytree(self.dutch, dest)
            path = dest / "hospital_2026.json"
            document = json.loads(path.read_text())
            document["blocks"][56]["text"] = "Tampered local extraction"
            path.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, "extraction differs"):
                build_handoff(dest, self.finlex, self.ledger_path, self.as_of)


if __name__ == "__main__":
    unittest.main()
