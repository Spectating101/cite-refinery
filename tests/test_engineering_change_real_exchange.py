"""The dossier receiver on the exact bytes exchanged in one HS → Policy Lab → HS replay.

The fixture directory is a verbatim copy of the exchange written by Hardware
Splicer's scripts/demo_change_dossier.py (Fielddeck 5, modeled values only):
three HS exports, four Policy Lab reviews and their verify receipts, two HS
proposals, two change packets and the HS revision heads r2 to r4.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cite_refinery.engineering_change_dossier import (
    ChangeEvidenceRejected, StaleEdition, build_dossier, check_currency, issue_dossier, render_markdown)

FIXTURE = Path(__file__).parent / "fixtures" / "hs_change_dossier_20261120"


class RealExchangeTests(unittest.TestCase):
    def packet(self) -> bytes:
        return (FIXTURE / "change-evidence.json").read_bytes()

    def test_real_exchange_issues_an_edition_that_keeps_the_runtime_failure(self):
        dossier, currency = issue_dossier(self.packet(), FIXTURE, (FIXTURE / "head-r2.json").read_bytes())
        self.assertEqual(currency["status"], "current")
        self.assertEqual(dossier["edition"]["bound_to"]["revision"], 2)
        failing = [row for row in dossier["checks"] if row["result"] == "FAIL"]
        self.assertEqual([row["check"] for row in failing], ["work_runtime"])
        self.assertLess(failing[0]["actual"], failing[0]["limit"])
        self.assertTrue(failing[0]["earlier_status"].startswith("stale"))
        self.assertFalse(dossier["physical_authority_granted"])
        text = render_markdown(dossier, currency).lower()
        self.assertNotIn("ready", text)
        self.assertNotIn("approved", text)

    def test_real_exchange_edition_is_stale_after_revision_3(self):
        dossier = build_dossier(self.packet(), FIXTURE)
        currency = check_currency(dossier, (FIXTURE / "head-r3.json").read_bytes())
        self.assertEqual(currency["status"], "stale")
        self.assertEqual(currency["head"]["revision"], 3)
        with self.assertRaises(StaleEdition):
            issue_dossier(self.packet(), FIXTURE, (FIXTURE / "head-r3.json").read_bytes())

    def test_real_exchange_refuses_a_changed_export(self):
        with TemporaryDirectory() as tmp:
            copy = Path(tmp) / "exchange"
            shutil.copytree(FIXTURE, copy)
            raw = (copy / "r2-export.json").read_bytes()
            (copy / "r2-export.json").write_bytes(raw.replace(b'"passed":false', b'"passed":true', 1))
            with self.assertRaisesRegex(ChangeEvidenceRejected, "SHA-256"):
                build_dossier(self.packet(), copy)

    def test_real_packet_hashes_name_every_fixture_file(self):
        packet = json.loads(self.packet())
        self.assertEqual({record["path"] for record in packet["files"].values()},
                         {"r1-export.json", "r1-review/review.json", "proposal.json", "r2-export.json",
                          "r2-review/review.json"})


    def test_real_candidate_edition_reports_the_native_runtime_and_goes_stale(self):
        packet = (FIXTURE / "change-evidence-r3.json").read_bytes()
        dossier, currency = issue_dossier(packet, FIXTURE, (FIXTURE / "head-r3.json").read_bytes())
        [row] = dossier["candidate_design_changes"]
        self.assertEqual((row["input"], row["before"], row["after"]), ("pi_work_current_a", 1, 0.697))
        self.assertEqual(row["native_outcome"]["native_value"], 4.002)
        self.assertIs(row["native_outcome"]["met"], True)
        self.assertEqual(row["physical_means"], "unknown / not tested")
        self.assertEqual([c["result"] for c in dossier["checks"]], ["pass (modeled)"] * 3)
        self.assertIn("unknown / not tested", render_markdown(dossier, currency))
        stale = check_currency(dossier, (FIXTURE / "head-r4.json").read_bytes())
        self.assertEqual(stale["status"], "stale")
        with self.assertRaises(StaleEdition):
            issue_dossier(packet, FIXTURE, (FIXTURE / "head-r4.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
