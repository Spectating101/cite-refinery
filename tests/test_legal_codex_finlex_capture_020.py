"""Finlex identity, transport rejection and archived-source integrity checks."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from xml.etree import ElementTree as ET

from scripts import legal_codex_capture_020 as capture


def structural_fixture() -> bytes:
    """A clearly artificial body to exercise structure, never the reviewed pin."""
    ns = capture.AKN
    root = ET.Element(f"{{{ns}}}akomaNtoso")
    judgment = ET.SubElement(root, f"{{{ns}}}judgment", name="main")
    meta = ET.SubElement(judgment, f"{{{ns}}}meta")
    identification = ET.SubElement(meta, f"{{{ns}}}identification")
    work = ET.SubElement(identification, f"{{{ns}}}FRBRWork")
    ET.SubElement(work, f"{{{ns}}}FRBRuri", value=capture.WORK_URI)
    ET.SubElement(work, f"{{{ns}}}FRBRthis", value=capture.WORK_URI + "/!main")
    ET.SubElement(work, f"{{{ns}}}FRBRalias", name="diaryNumber", value=capture.IDENTITY)
    ET.SubElement(work, f"{{{ns}}}FRBRdate", name="dateIssued", date=capture.ISSUED_DATE)
    expression = ET.SubElement(identification, f"{{{ns}}}FRBRExpression")
    ET.SubElement(expression, f"{{{ns}}}FRBRuri", value=capture.WORK_URI + "/fin@")
    ET.SubElement(expression, f"{{{ns}}}FRBRlanguage", language="fin")
    ET.SubElement(expression, f"{{{ns}}}FRBRdate", name="dateIssued", date=capture.ISSUED_DATE)
    manifestation = ET.SubElement(identification, f"{{{ns}}}FRBRManifestation")
    ET.SubElement(manifestation, f"{{{ns}}}FRBRformat", value="xml")
    ET.SubElement(manifestation, f"{{{ns}}}FRBRdate", name="dateProduced", date="2026-11-10")
    body = ET.SubElement(judgment, f"{{{ns}}}judgmentBody")
    for number in range(1, 68):
        ET.SubElement(body, f"{{{ns}}}p").text = f"{number}. Synthetic paragraph; no real case assertion."
    ET.SubElement(body, f"{{{ns}}}p").text = capture.FINALITY_TEXT
    return ET.tostring(root, encoding="utf-8")


class FinlexStructure020Tests(unittest.TestCase):
    def extract(self, raw):
        return capture.extract(raw, require_pin=False)

    def test_structural_fixture_separates_production_and_decision_dates(self):
        result = self.extract(structural_fixture())
        self.assertEqual(result["metadata"]["publication_values"], [])
        self.assertEqual(result["metadata"]["produced_dates"], ["2026-11-10"])
        self.assertEqual(result["date"], "2026-10-23")
        self.assertEqual(result["blocks"][-1]["id"], "p_finality")
        self.assertEqual(result["metadata"]["decision_finality"], "not_final_as_published")

    def test_html_shell_cannot_pass_just_by_containing_the_case_number(self):
        raw = b"<html><body>TSV/238/2022 is in a navigation shell only.</body></html>"
        with self.assertRaisesRegex(ValueError, "HTML shell"):
            self.extract(raw)

    def test_wrong_diary_and_wrong_work_uri_are_rejected(self):
        raw = structural_fixture()
        for altered in (
            raw.replace(b"TSV/238/2022", b"TSV/999/2022"),
            raw.replace(capture.WORK_URI.encode(), capture.WORK_URI.replace("/37", "/38").encode()),
        ):
            with self.subTest(altered=altered[:40]):
                with self.assertRaisesRegex(ValueError, "identity|URI"):
                    self.extract(altered)

    def test_expression_date_cannot_conflict_with_decision_date(self):
        root = ET.fromstring(structural_fixture())
        element = root.find(".//akn:FRBRExpression/akn:FRBRdate", capture.NS)
        element.set("date", "2026-11-10")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.extract(ET.tostring(root, encoding="utf-8"))

    def test_missing_duplicate_and_out_of_order_paragraphs_are_rejected(self):
        for mode in ("missing", "duplicate", "reordered"):
            root = ET.fromstring(structural_fixture())
            body = root.find(".//akn:judgmentBody", capture.NS)
            first = body[0]
            if mode == "missing":
                body.remove(first)
            elif mode == "duplicate":
                body.insert(1, deepcopy(first))
            else:
                body.remove(first)
                body.insert(1, first)
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "1..67"):
                    self.extract(ET.tostring(root, encoding="utf-8"))

    def test_malformed_xml_and_entity_declarations_are_rejected(self):
        raw = structural_fixture()
        for altered in (raw[:-8], b'<!DOCTYPE akomaNtoso [<!ENTITY test "value">]>' + raw):
            with self.assertRaisesRegex(ValueError, "XML|declarations"):
                self.extract(altered)

    def test_nonfinal_statement_must_not_be_missing_or_rewritten(self):
        raw = structural_fixture().replace(capture.FINALITY_TEXT.encode(), b"Decision is final.")
        with self.assertRaisesRegex(ValueError, "nonfinal"):
            self.extract(raw)

    def test_structural_validity_does_not_bypass_default_raw_pin(self):
        with self.assertRaisesRegex(ValueError, "reviewed raw pin"):
            capture.extract(structural_fixture())

    def test_capture_timestamp_must_be_timezone_aware(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            capture.extract(structural_fixture(), require_pin=False, captured_at="2026-11-18T09:00:00")


class _Response(io.BytesIO):
    status = 200

    def __init__(self, raw, *, content_type="application/xml", declared_length=None):
        super().__init__(raw)
        self.headers = {"Content-Type": content_type}
        if declared_length is not None:
            self.headers["Content-Length"] = str(declared_length)

    def geturl(self):
        return capture.SOURCE_URL


class FinlexTransport020Tests(unittest.TestCase):
    def run_fetch(self, response):
        with patch.object(capture, "build_opener") as opener:
            opener.return_value.open.return_value = response
            return capture.fetch()

    def test_html_content_type_is_rejected_even_for_plausible_body(self):
        with self.assertRaisesRegex(ValueError, "not XML"):
            self.run_fetch(_Response(structural_fixture(), content_type="text/html"))

    def test_byte_budget_and_truncated_content_length_are_rejected(self):
        for response in (
            _Response(b"x" * (capture.MAX_BYTES + 1)),
            _Response(b"x" * 100, declared_length=101),
            _Response(b"small", declared_length=capture.MAX_BYTES + 1),
        ):
            with self.assertRaisesRegex(ValueError, "byte budget|Content-Length"):
                self.run_fetch(response)

    def test_redirect_handler_refuses_following_even_same_origin(self):
        request = capture.Request(capture.SOURCE_URL)
        for target in ("https://example.invalid/other", capture.SOURCE_URL + "?changed=1"):
            with self.assertRaisesRegex(HTTPError, "redirect refused"):
                capture._NoRedirect().redirect_request(request, None, 302, "Found", {}, target)

    def test_elapsed_budget_stops_an_incomplete_response(self):
        with patch.object(capture.time, "monotonic", side_effect=[0, 61]):
            with self.assertRaisesRegex(TimeoutError, "elapsed-time"):
                self.run_fetch(_Response(structural_fixture()))

    def test_failed_network_attempt_leaves_failed_receipt_without_verified_tls(self):
        with TemporaryDirectory() as temp:
            dest = Path(temp) / "capture"
            with patch.object(capture, "fetch", side_effect=TimeoutError("connection timed out")):
                result = capture.capture(dest)
            self.assertEqual(result["status"], "failed")
            self.assertIs(result["tls_hostname_verified"], False)
            self.assertIsNone(result["raw_sha256"])
            self.assertEqual(sorted(p.name for p in dest.iterdir()), ["receipt.json"])
            with self.assertRaisesRegex(ValueError, "receipt"):
                capture.load(dest)

    def test_unreviewed_fetch_does_not_leave_admissible_source_files(self):
        with TemporaryDirectory() as temp:
            dest = Path(temp) / "capture"
            with patch.object(capture, "fetch", return_value=(structural_fixture(), "application/xml", capture.SOURCE_URL)):
                result = capture.capture(dest)
            self.assertEqual(result["status"], "failed")
            self.assertIn("reviewed raw pin", result["detail"])
            self.assertEqual(sorted(p.name for p in dest.iterdir()), ["receipt.json"])


@unittest.skipUnless(os.environ.get("LEGAL_CODEX_020_FINLEX"), "Actual 020 Finlex capture required")
class ActualFinlex020Tests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(os.environ["LEGAL_CODEX_020_FINLEX"])

    def test_actual_source_passes_pin_identity_receipt_and_reextraction(self):
        source = capture.load(self.folder)
        self.assertEqual(source["raw_sha256"], capture.PINNED_SHA256)
        self.assertEqual(source["identity"], "TSV/238/2022")
        self.assertEqual(len(source["blocks"]), 68)
        self.assertEqual(source["blocks"][64]["id"], "p0065")
        self.assertIn("1.1.2018–13.4.2019", source["blocks"][64]["text"])
        self.assertIn("14.5.2019–28.11.2021", source["blocks"][51]["text"])

    def test_actual_source_keeps_production_date_out_of_publication_metadata(self):
        source = capture.load(self.folder)
        self.assertEqual(source["metadata"]["publication_values"], [])
        self.assertEqual(source["metadata"]["produced_dates"], ["2026-11-10"])
        self.assertEqual(source["metadata"]["decision_finality"], "not_final_as_published")

    def test_modified_extraction_and_unverified_receipt_are_rejected(self):
        for mode in ("extraction", "tls", "duplicate_json_key"):
            with self.subTest(mode=mode), TemporaryDirectory() as temp:
                dest = Path(temp) / "copy"
                shutil.copytree(self.folder, dest)
                if mode == "extraction":
                    path = dest / f"{capture.SOURCE_ID}.json"
                    value = json.loads(path.read_text())
                    value["metadata"]["decision_finality"] = "final"
                    path.write_text(json.dumps(value))
                else:
                    path = dest / "receipt.json"
                    if mode == "tls":
                        value = json.loads(path.read_text())
                        value["tls_hostname_verified"] = False
                        path.write_text(json.dumps(value))
                    else:
                        path.write_text(path.read_text().rstrip()[:-1] + ', "status": "captured_and_reextracted"}')
                with self.assertRaisesRegex(ValueError, "extraction differs|verified TLS|duplicate JSON"):
                    capture.load(dest)

    def test_raw_modification_cannot_be_authorized_by_a_rewritten_receipt_hash(self):
        with TemporaryDirectory() as temp:
            dest = Path(temp) / "copy"
            shutil.copytree(self.folder, dest)
            path = dest / f"{capture.SOURCE_ID}.xml"
            path.write_bytes(path.read_bytes() + b"\n")
            receipt_path = dest / "receipt.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["raw_sha256"] = capture.digest(path.read_bytes())
            receipt["raw_bytes"] = path.stat().st_size
            receipt_path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "pin"):
                capture.load(dest)


if __name__ == "__main__":
    unittest.main()
