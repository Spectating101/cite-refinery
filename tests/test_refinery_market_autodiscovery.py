import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cite_refinery.solution import ReviewedMarketCLIAdapter


class ReviewedMarketAutoDiscoveryTests(unittest.TestCase):
    def test_canonical_restored_path_is_detected_without_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            canonical = home / ".local" / "share" / "refinery" / "reviewed-market-search.db"
            canonical.parent.mkdir(parents=True)
            canonical.write_bytes(b"fixture")
            with patch.dict(os.environ, {"HOME": str(home)}, clear=False):
                os.environ.pop("REFINERY_MARKET_DB", None)
                adapter = ReviewedMarketCLIAdapter(command=sys.executable)
            self.assertEqual(adapter.db_path, str(canonical.resolve()))
            self.assertEqual(adapter.db_source, "canonical_restored_path")
            self.assertTrue(adapter.available())

    def test_environment_override_wins_over_canonical_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            canonical = home / ".local" / "share" / "refinery" / "reviewed-market-search.db"
            canonical.parent.mkdir(parents=True)
            canonical.write_bytes(b"canonical")
            override = Path(tmp) / "override.db"
            override.write_bytes(b"override")
            with patch.dict(
                os.environ,
                {"HOME": str(home), "REFINERY_MARKET_DB": str(override)},
                clear=False,
            ):
                adapter = ReviewedMarketCLIAdapter(command=sys.executable)
            self.assertEqual(adapter.db_path, str(override.resolve()))
            self.assertEqual(adapter.db_source, "environment")

    def test_explicit_path_wins_over_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            explicit = Path(tmp) / "explicit.db"
            env_db = Path(tmp) / "env.db"
            explicit.write_bytes(b"explicit")
            env_db.write_bytes(b"env")
            with patch.dict(os.environ, {"REFINERY_MARKET_DB": str(env_db)}, clear=False):
                adapter = ReviewedMarketCLIAdapter(command=sys.executable, db_path=str(explicit))
            self.assertEqual(adapter.db_path, str(explicit.resolve()))
            self.assertEqual(adapter.db_source, "explicit")

    def test_no_database_explains_restore_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"HOME": tmp}, clear=False):
                os.environ.pop("REFINERY_MARKET_DB", None)
                adapter = ReviewedMarketCLIAdapter(command=sys.executable)
                result = adapter.search("provenance")
            self.assertEqual(result.status, "not_run")
            self.assertIn("refinery-market-snapshot restore", result.raw)


if __name__ == "__main__":
    unittest.main()
