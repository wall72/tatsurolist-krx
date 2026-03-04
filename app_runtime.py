from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

APP_HOME_DIR = Path.home() / ".tatsurolist-krx"
CONFIG_PATH = APP_HOME_DIR / "config.json"
LOG_PATH = APP_HOME_DIR / "app.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "market": "KOSPI",
    "date": "",
    "cap_min_eok": 5000,
    "cap_max_eok": 10000,
    "top_n": 10,
    "per_max": "",
    "pbr_max": "",
    "div_policy": "zero",
    "backtest_start_date": "",
    "backtest_end_date": "",
    "backtest_scope": "all",
}


def setup_file_logging(log_path: Path = LOG_PATH) -> Path:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    abs_log_path = str(log_path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == abs_log_path:
            return log_path

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    return log_path


def load_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not config_path.exists():
        return dict(DEFAULT_CONFIG)

    with config_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    config = dict(DEFAULT_CONFIG)
    if isinstance(raw, dict):
        config.update(raw)

    return config


def save_config(config: dict[str, Any], config_path: Path = CONFIG_PATH) -> Path:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(DEFAULT_CONFIG)
    payload.update(config)
    payload["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with config_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return config_path
