from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import krx_backtest as bt


class BacktestDateTests(unittest.TestCase):
    def test_generate_month_end_dates(self):
        dates = bt.generate_month_end_dates("2026-01-01", "2026-03-31")
        self.assertEqual(dates, ["20260131", "20260228", "20260331"])

    def test_generate_month_end_dates_reject_invalid_range(self):
        with self.assertRaisesRegex(ValueError, "start_date"):
            bt.generate_month_end_dates("2026-03-01", "2026-01-01")


class BacktestSummaryTests(unittest.TestCase):
    def test_summarize_backtest_calculates_cumulative_and_mdd(self):
        df = pd.DataFrame(
            {
                "portfolio_return": [0.1, -0.2, 0.05],
                "benchmark_return": [0.01, -0.03, 0.02],
            }
        )

        summary = bt.summarize_backtest(df)

        self.assertEqual(summary["periods"], 3)
        self.assertAlmostEqual(summary["portfolio_cumulative_return"], -0.076, places=6)
        self.assertAlmostEqual(summary["benchmark_cumulative_return"], -0.000706, places=6)
        self.assertLess(summary["portfolio_mdd"], 0)


class BacktestReportTests(unittest.TestCase):
    @patch("krx_backtest.run_monthly_rebalance_backtest")
    def test_create_market_comparison_report(self, mock_run_backtest):
        mock_run_backtest.side_effect = [
            pd.DataFrame({"portfolio_return": [0.1], "benchmark_return": [0.01]}),
            pd.DataFrame({"portfolio_return": [0.2], "benchmark_return": [0.05]}),
        ]

        config = bt.BacktestConfig(start_date="2026-01-01", end_date="2026-03-31")
        summary_df, market_results = bt.create_market_comparison_report(config=config)

        self.assertEqual(list(summary_df["market"]), ["KOSPI", "KOSDAQ"])
        self.assertIn("KOSPI", market_results)
        self.assertIn("KOSDAQ", market_results)

    def test_write_backtest_report_outputs_files(self):
        summary_df = pd.DataFrame(
            {
                "market": ["KOSPI"],
                "periods": [1],
                "portfolio_cumulative_return": [0.1],
                "benchmark_cumulative_return": [0.05],
                "portfolio_mdd": [-0.02],
                "benchmark_mdd": [-0.01],
            }
        )
        market_results = {"KOSPI": pd.DataFrame({"a": [1]})}

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = bt.write_backtest_report(tmpdir, summary_df, market_results)
            self.assertTrue(report_path.exists())
            self.assertTrue((Path(tmpdir) / "backtest_summary.csv").exists())
            self.assertTrue((Path(tmpdir) / "backtest_kospi_monthly.csv").exists())


if __name__ == "__main__":
    unittest.main()
