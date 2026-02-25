from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from pykrx import stock

from krx_value_service import get_tatsuro_small_mid_value_top10


@dataclass
class BacktestConfig:
    start_date: str
    end_date: str
    top_n: int = 10
    cap_min: int = 500_000_000_000
    cap_max: int = 1_000_000_000_000
    per_max: Optional[float] = None
    pbr_max: Optional[float] = None
    div_policy: str = "zero"


def _to_yyyymmdd(value: str) -> str:
    raw = value.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    raise ValueError("date must be YYYYMMDD or YYYY-MM-DD")


def generate_month_end_dates(start_date: str, end_date: str) -> list[str]:
    start = pd.Timestamp(_to_yyyymmdd(start_date))
    end = pd.Timestamp(_to_yyyymmdd(end_date))
    if start > end:
        raise ValueError("start_date must be earlier than or equal to end_date")

    month_ends = pd.date_range(start=start, end=end, freq="ME")
    dates = [d.strftime("%Y%m%d") for d in month_ends if start <= d <= end]
    if not dates:
        dates = [end.strftime("%Y%m%d")]
    return dates


def _calculate_mdd(return_series: pd.Series) -> float:
    cumulative = (1 + return_series.fillna(0.0)).cumprod()
    peak = cumulative.cummax()
    drawdown = cumulative / peak - 1
    return float(drawdown.min()) if not drawdown.empty else 0.0


def _calculate_total_return(return_series: pd.Series) -> float:
    if return_series.empty:
        return 0.0
    return float((1 + return_series.fillna(0.0)).prod() - 1)


def _build_rebalance_pairs(rebalance_dates: Iterable[str]) -> list[tuple[str, str]]:
    dates = list(rebalance_dates)
    return [(dates[i], dates[i + 1]) for i in range(len(dates) - 1)]


def _portfolio_monthly_return(tickers: list[str], buy_date: str, sell_date: str) -> float:
    if not tickers:
        return 0.0

    returns: list[float] = []
    for ticker in tickers:
        try:
            prices = stock.get_market_ohlcv_by_date(buy_date, sell_date, ticker)
            if prices.empty:
                continue
            buy_price = float(prices.iloc[0]["종가"])
            sell_price = float(prices.iloc[-1]["종가"])
            if buy_price <= 0:
                continue
            returns.append(sell_price / buy_price - 1)
        except Exception:
            continue

    if not returns:
        return 0.0
    return float(sum(returns) / len(returns))


def _benchmark_monthly_return(market: str, buy_date: str, sell_date: str) -> float:
    index_ticker = "1001" if market == "KOSPI" else "2001"
    prices = stock.get_index_ohlcv_by_date(buy_date, sell_date, index_ticker)
    if prices.empty:
        return 0.0
    buy_price = float(prices.iloc[0]["종가"])
    sell_price = float(prices.iloc[-1]["종가"])
    if buy_price <= 0:
        return 0.0
    return float(sell_price / buy_price - 1)


def run_monthly_rebalance_backtest(market: str, config: BacktestConfig) -> pd.DataFrame:
    rebalance_dates = generate_month_end_dates(config.start_date, config.end_date)
    pairs = _build_rebalance_pairs(rebalance_dates)

    rows: list[dict] = []
    for buy_date, sell_date in pairs:
        selected_df, used_date, _, _ = get_tatsuro_small_mid_value_top10(
            market=market,
            date=buy_date,
            cap_min=config.cap_min,
            cap_max=config.cap_max,
            top_n=config.top_n,
            per_max=config.per_max,
            pbr_max=config.pbr_max,
            div_policy=config.div_policy,
        )

        tickers = selected_df.index.tolist()
        portfolio_ret = _portfolio_monthly_return(tickers=tickers, buy_date=used_date, sell_date=sell_date)
        benchmark_ret = _benchmark_monthly_return(market=market, buy_date=used_date, sell_date=sell_date)

        rows.append(
            {
                "market": market,
                "rebalance_date": used_date,
                "next_rebalance_date": sell_date,
                "selected_count": len(tickers),
                "portfolio_return": portfolio_ret,
                "benchmark_return": benchmark_ret,
                "excess_return": portfolio_ret - benchmark_ret,
            }
        )

    result_df = pd.DataFrame(rows)
    if result_df.empty:
        return result_df

    result_df["portfolio_cumulative"] = (1 + result_df["portfolio_return"]).cumprod() - 1
    result_df["benchmark_cumulative"] = (1 + result_df["benchmark_return"]).cumprod() - 1
    result_df["excess_cumulative"] = result_df["portfolio_cumulative"] - result_df["benchmark_cumulative"]
    return result_df


def summarize_backtest(result_df: pd.DataFrame) -> dict[str, float]:
    if result_df.empty:
        return {
            "periods": 0,
            "portfolio_cumulative_return": 0.0,
            "benchmark_cumulative_return": 0.0,
            "portfolio_mdd": 0.0,
            "benchmark_mdd": 0.0,
        }

    portfolio_returns = result_df["portfolio_return"]
    benchmark_returns = result_df["benchmark_return"]

    return {
        "periods": int(len(result_df)),
        "portfolio_cumulative_return": _calculate_total_return(portfolio_returns),
        "benchmark_cumulative_return": _calculate_total_return(benchmark_returns),
        "portfolio_mdd": _calculate_mdd(portfolio_returns),
        "benchmark_mdd": _calculate_mdd(benchmark_returns),
    }


def create_market_comparison_report(
    config: BacktestConfig,
    markets: Iterable[str] = ("KOSPI", "KOSDAQ"),
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    summaries: list[dict] = []
    market_results: dict[str, pd.DataFrame] = {}

    for market in markets:
        market_df = run_monthly_rebalance_backtest(market=market, config=config)
        market_results[market] = market_df
        summary = summarize_backtest(market_df)
        summary["market"] = market
        summaries.append(summary)

    summary_df = pd.DataFrame(summaries)[
        [
            "market",
            "periods",
            "portfolio_cumulative_return",
            "benchmark_cumulative_return",
            "portfolio_mdd",
            "benchmark_mdd",
        ]
    ]
    return summary_df, market_results


def write_backtest_report(output_dir: str, summary_df: pd.DataFrame, market_results: dict[str, pd.DataFrame]) -> Path:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    summary_path = target_dir / "backtest_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    for market, market_df in market_results.items():
        market_df.to_csv(target_dir / f"backtest_{market.lower()}_monthly.csv", index=False, encoding="utf-8-sig")

    md_path = target_dir / "backtest_report.md"
    lines = ["# Monthly Rebalance Backtest Report", "", "## Summary", ""]
    header = "| " + " | ".join(summary_df.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(summary_df.columns)) + " |"
    lines.extend([header, separator])
    for row in summary_df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return md_path
