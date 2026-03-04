from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app_runtime import DEFAULT_CONFIG, load_config, save_config, setup_file_logging


class AppRuntimeTests(unittest.TestCase):
    def test_load_config_returns_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "missing.json"
            cfg = load_config(config_path=config_path)

        self.assertEqual(cfg, DEFAULT_CONFIG)

    def test_save_and_load_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            payload = {
                "market": "KOSDAQ",
                "top_n": 15,
                "div_policy": "exclude",
            }
            save_config(payload, config_path=config_path)
            loaded = load_config(config_path=config_path)

            self.assertEqual(loaded["market"], "KOSDAQ")
            self.assertEqual(loaded["top_n"], 15)
            self.assertEqual(loaded["div_policy"], "exclude")
            self.assertIn("cap_min_eok", loaded)

            raw = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("saved_at", raw)

    def test_setup_file_logging_creates_log_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "app.log"
            out = setup_file_logging(log_path=log_path)

            self.assertEqual(out, log_path)
            self.assertTrue(log_path.exists())


if __name__ == "__main__":
    unittest.main()
