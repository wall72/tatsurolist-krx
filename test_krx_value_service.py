from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

import krx_value_service as svc


class NormalizeMarketTests(unittest.TestCase):
    def test_normalize_market_accepts_lowercase_and_spaces(self):
        self.assertEqual(svc.normalize_market(" kospi "), "KOSPI")

    def test_normalize_market_rejects_invalid_market(self):
        with self.assertRaisesRegex(ValueError, "market must be one of"):
            svc.normalize_market("NASDAQ")


class NormalizeDateTests(unittest.TestCase):
    def test_normalize_date_accepts_yyyymmdd(self):
        parsed = svc.normalize_date("20260219")
        self.assertEqual(parsed, datetime(2026, 2, 19))

    def test_normalize_date_accepts_iso_date(self):
        parsed = svc.normalize_date("2026-02-19")
        self.assertEqual(parsed, datetime(2026, 2, 19))

    def test_normalize_date_rejects_invalid_format(self):
        with self.assertRaisesRegex(ValueError, "date must be YYYYMMDD or YYYY-MM-DD"):
            svc.normalize_date("2026/02/19")


class TatsuroScoreTests(unittest.TestCase):
    def test_get_tatsuro_score_includes_per_pbr_div(self):
        row = pd.Series({"PER": 10.0, "PBR": 2.0, "DIV": 3.0})
        score = svc.get_tatsuro_score(row)
        self.assertAlmostEqual(score, 0.1 + 0.5 + 0.03, places=8)

    def test_get_tatsuro_score_ignores_non_positive_or_nan_values(self):
        row = pd.Series({"PER": -1.0, "PBR": 0.0, "DIV": float("nan")})
        score = svc.get_tatsuro_score(row)
        self.assertEqual(score, 0.0)


class FilterConditionTests(unittest.TestCase):
    def setUp(self):
        svc._QUERY_CACHE.clear()
        svc._TICKER_NAME_CACHE.clear()

    @patch("krx_value_service.add_ticker_names")
    @patch("krx_value_service.get_market_data_with_fallback")
    def test_filter_conditions_for_per_pbr_market_cap_and_per_pbr_caps(self, mock_get_market_data, mock_add_ticker_names):
        idx = ["A", "B", "C", "D", "E"]
        market_cap_df = pd.DataFrame(
            {
                "시가총액": [600_000_000_000, 600_000_000_000, 700_000_000_000, 600_000_000_000, 900_000_000_000]
            },
            index=idx,
        )
        fundamental_df = pd.DataFrame(
            {
                "PER": [10.0, 16.0, 8.0, 9.0, 7.0],
                "PBR": [1.0, 1.0, 4.0, -1.0, 1.0],
                "DIV": [2.0, 2.0, 2.0, 2.0, 2.0],
            },
            index=idx,
        )

        mock_get_market_data.return_value = (market_cap_df, fundamental_df, "20260219")

        def add_names(df: pd.DataFrame) -> pd.DataFrame:
            out = df.copy()
            out["종목명"] = [f"name-{ticker}" for ticker in out.index]
            return out

        mock_add_ticker_names.side_effect = add_names

        result_df, used_date, stats, logs = svc.get_tatsuro_small_mid_value_top10(
            market="KOSPI",
            date="2026-02-19",
            cap_min=500_000_000_000,
            cap_max=1_000_000_000_000,
            top_n=10,
            per_max=12.0,
            pbr_max=2.0,
        )

        self.assertEqual(used_date, "20260219")
        self.assertEqual(stats, {"total": 5, "filtered": 2, "final": 2, "cache_hit": 0})
        self.assertEqual(result_df.iloc[0]["종목명"], "name-E")
        self.assertIsInstance(logs, list)

    @patch("krx_value_service.add_ticker_names")
    @patch("krx_value_service.get_market_data_with_fallback")
    def test_div_policy_exclude_filters_out_nan_div(self, mock_get_market_data, mock_add_ticker_names):
        idx = ["A", "B"]
        market_cap_df = pd.DataFrame({"시가총액": [600_000_000_000, 650_000_000_000]}, index=idx)
        fundamental_df = pd.DataFrame(
            {
                "PER": [10.0, 8.0],
                "PBR": [1.0, 1.0],
                "DIV": [float("nan"), 2.0],
            },
            index=idx,
        )
        mock_get_market_data.return_value = (market_cap_df, fundamental_df, "20260219")

        def add_names(df: pd.DataFrame) -> pd.DataFrame:
            out = df.copy()
            out["종목명"] = [f"name-{ticker}" for ticker in out.index]
            return out

        mock_add_ticker_names.side_effect = add_names

        result_df, _, stats, _ = svc.get_tatsuro_small_mid_value_top10(div_policy="exclude")

        self.assertEqual(stats["filtered"], 1)
        self.assertEqual(stats["final"], 1)
        self.assertEqual(result_df.iloc[0]["종목명"], "name-B")

    @patch("krx_value_service.add_ticker_names")
    @patch("krx_value_service.get_market_data_with_fallback")
    def test_same_params_use_query_cache(self, mock_get_market_data, mock_add_ticker_names):
        idx = ["A"]
        market_cap_df = pd.DataFrame({"시가총액": [600_000_000_000]}, index=idx)
        fundamental_df = pd.DataFrame({"PER": [10.0], "PBR": [1.0], "DIV": [2.0]}, index=idx)
        mock_get_market_data.return_value = (market_cap_df, fundamental_df, "20260219")

        def add_names(df: pd.DataFrame) -> pd.DataFrame:
            out = df.copy()
            out["종목명"] = ["name-A"]
            return out

        mock_add_ticker_names.side_effect = add_names

        _, _, stats1, _ = svc.get_tatsuro_small_mid_value_top10(date="2026-02-19")
        _, _, stats2, _ = svc.get_tatsuro_small_mid_value_top10(date="2026-02-19")

        self.assertEqual(stats1["cache_hit"], 0)
        self.assertEqual(stats2["cache_hit"], 1)
        self.assertEqual(mock_get_market_data.call_count, 1)


if __name__ == "__main__":
    unittest.main()
