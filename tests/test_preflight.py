import tempfile
import unittest
from pathlib import Path

from cite_refinery.preflight import build_preflight


class FakeCommandAdapter:
    def __init__(self, available: bool, command=None):
        self._available = available
        self.command = command or ["fake-command"]

    def available(self):
        return self._available


class FakeMarketAdapter:
    def __init__(self, db_path=None, command=None, db_source="fixture"):
        self.db_path = db_path
        self.command = command or ["/definitely/missing/refinery-market-search"]
        self.db_source = db_source


class PreflightTests(unittest.TestCase):
    def test_core_can_be_ready_while_broad_market_supply_is_degraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_preflight(
                Path(tmp) / "workspace",
                cite=FakeCommandAdapter(True),
                cite_research=FakeCommandAdapter(True),
                canonical_refinery=FakeCommandAdapter(True),
                reviewed_market=FakeMarketAdapter(),
            )
            self.assertTrue(report["core_ready"])
            self.assertFalse(report["full_broad_supply_ready"])
            self.assertEqual(report["required_failures"], [])
            self.assertEqual(
                set(report["broad_supply_degradations"]),
                {"refinery_reviewed_market_database", "refinery_reviewed_market_search"},
            )

    def test_missing_required_cite_surface_fails_core_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_preflight(
                tmp,
                cite=FakeCommandAdapter(False),
                cite_research=FakeCommandAdapter(True),
                canonical_refinery=FakeCommandAdapter(True),
                reviewed_market=FakeMarketAdapter(),
            )
            self.assertFalse(report["core_ready"])
            self.assertIn("cite_grounding", report["required_failures"])

    def test_full_supply_ready_when_all_commands_and_database_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "reviewed-market.db"
            db.write_bytes(b"fixture")
            # Python itself is a stable executable path for command-availability checking.
            import sys
            report = build_preflight(
                Path(tmp) / "workspace",
                cite=FakeCommandAdapter(True),
                cite_research=FakeCommandAdapter(True),
                canonical_refinery=FakeCommandAdapter(True),
                reviewed_market=FakeMarketAdapter(db_path=str(db), command=[sys.executable]),
            )
            self.assertTrue(report["core_ready"])
            self.assertTrue(report["full_broad_supply_ready"])
            self.assertTrue(report["feedback_protocol_ready"])
            statuses = {row["name"]: row["status"] for row in report["checks"]}
            self.assertEqual(statuses["refinery_reviewed_market_database"], "ready")
            self.assertEqual(statuses["refinery_reviewed_market_search"], "ready")


if __name__ == "__main__":
    unittest.main()
