from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from pykrx import stock

VALID_MARKETS = {"KOSPI", "KOSDAQ"}


def normalize_market(market: str) -> str:
    normalized = market.strip().upper()
    if normalized not in VALID_MARKETS:
        raise ValueError("market must be one of: KOSPI, KOSDAQ")
    return normalized


def normalize_date(date: Optional[str]) -> datetime:
    if not date:
        return datetime.now()

    raw = date.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    raise ValueError("date must be YYYYMMDD or YYYY-MM-DD")


def get_market_data_with_fallback(market: str, base_date: datetime, max_backtrack_days: int = 14):
    for offset in range(max_backtrack_days + 1):
        target_date = (base_date - timedelta(days=offset)).strftime("%Y%m%d")
        try:
            market_cap_df = stock.get_market_cap_by_ticker(target_date, market=market)
            fundamental_df = stock.get_market_fundamental_by_ticker(target_date, market=market)
            if not market_cap_df.empty and not fundamental_df.empty:
                return market_cap_df, fundamental_df, target_date
        except Exception:
            continue

    raise RuntimeError(f"No market data available for {market} in last {max_backtrack_days + 1} days")


def add_ticker_names(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["종목명"] = [stock.get_market_ticker_name(ticker) for ticker in result.index]
    return result


def get_tatsuro_score(row: pd.Series) -> float:
    score = 0.0

    if pd.notna(row["PER"]) and row["PER"] > 0:
        score += 1 / row["PER"]

    if pd.notna(row["PBR"]) and row["PBR"] > 0:
        score += 1 / row["PBR"]

    if pd.notna(row["DIV"]):
        score += row["DIV"] / 100

    return score


def get_tatsuro_small_mid_value_top10(
    market: str = "KOSPI",
    date: Optional[str] = None,
    cap_min: int = 500_000_000_000,
    cap_max: int = 1_000_000_000_000,
    top_n: int = 10,
):
    normalized_market = normalize_market(market)
    base_date = normalize_date(date)

    market_cap_df, fundamental_df, used_date = get_market_data_with_fallback(
        market=normalized_market,
        base_date=base_date,
    )

    result_df = market_cap_df.join(fundamental_df, how="inner")

    result_df = result_df[
        (result_df["PER"] > 0)
        & (result_df["PBR"] > 0)
        & (result_df["시가총액"] >= cap_min)
        & (result_df["시가총액"] <= cap_max)
    ]

    result_df = add_ticker_names(result_df)
    result_df["TAT"] = result_df.apply(get_tatsuro_score, axis=1)

    result_df = result_df.sort_values("TAT", ascending=False).head(top_n)

    display_df = result_df[["종목명", "시가총액", "PER", "PBR", "DIV", "TAT"]].copy()
    display_df["시가총액(조)"] = (display_df["시가총액"] / 1_000_000_000_000).round(3)
    display_df = display_df.drop(columns=["시가총액"])
    display_df["TAT"] = display_df["TAT"].round(4)

    return display_df, used_date
