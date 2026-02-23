from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from pykrx import stock

VALID_MARKETS = {"KOSPI", "KOSDAQ"}
VALID_DIV_POLICIES = {"zero", "exclude"}

_TICKER_NAME_CACHE: dict[str, str] = {}
_QUERY_CACHE: dict[tuple, tuple[pd.DataFrame, str, dict[str, int], list[str]]] = {}


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


def get_market_data_with_fallback(
    market: str,
    base_date: datetime,
    max_backtrack_days: int = 14,
    backtrack_logs: Optional[list[str]] = None,
):
    for offset in range(max_backtrack_days + 1):
        target_date = (base_date - timedelta(days=offset)).strftime("%Y%m%d")
        try:
            market_cap_df = stock.get_market_cap_by_ticker(target_date, market=market)
            fundamental_df = stock.get_market_fundamental_by_ticker(target_date, market=market)
            if not market_cap_df.empty and not fundamental_df.empty:
                if backtrack_logs is not None:
                    if offset == 0:
                        backtrack_logs.append(f"{target_date}: 입력 기준일 데이터 사용")
                    else:
                        backtrack_logs.append(
                            f"{target_date}: {offset}일 백트래킹 후 사용"
                        )
                return market_cap_df, fundamental_df, target_date
            if backtrack_logs is not None:
                backtrack_logs.append(f"{target_date}: 데이터 없음(빈 결과)")
        except Exception:
            if backtrack_logs is not None:
                backtrack_logs.append(f"{target_date}: 조회 실패(예외 발생)")
            continue

    raise RuntimeError(f"No market data available for {market} in last {max_backtrack_days + 1} days")


def add_ticker_names(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    names: list[str] = []
    for ticker in result.index:
        if ticker not in _TICKER_NAME_CACHE:
            _TICKER_NAME_CACHE[ticker] = stock.get_market_ticker_name(ticker)
        names.append(_TICKER_NAME_CACHE[ticker])
    result["종목명"] = names
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


def get_tatsuro_contributions(row: pd.Series) -> tuple[float, float, float]:
    per_contrib = 1 / row["PER"] if pd.notna(row["PER"]) and row["PER"] > 0 else 0.0
    pbr_contrib = 1 / row["PBR"] if pd.notna(row["PBR"]) and row["PBR"] > 0 else 0.0
    div_contrib = row["DIV"] / 100 if pd.notna(row["DIV"]) else 0.0
    return per_contrib, pbr_contrib, div_contrib


def get_tatsuro_small_mid_value_top10(
    market: str = "KOSPI",
    date: Optional[str] = None,
    cap_min: int = 500_000_000_000,
    cap_max: int = 1_000_000_000_000,
    top_n: int = 10,
    per_max: Optional[float] = None,
    pbr_max: Optional[float] = None,
    div_policy: str = "zero",
):
    normalized_market = normalize_market(market)
    base_date = normalize_date(date)
    normalized_div_policy = div_policy.strip().lower()
    if normalized_div_policy not in VALID_DIV_POLICIES:
        raise ValueError("div_policy must be one of: zero, exclude")

    cache_key = (
        normalized_market,
        base_date.strftime("%Y%m%d"),
        cap_min,
        cap_max,
        top_n,
        per_max,
        pbr_max,
        normalized_div_policy,
    )
    if cache_key in _QUERY_CACHE:
        cached_df, cached_used_date, cached_stats, cached_logs = _QUERY_CACHE[cache_key]
        stats = dict(cached_stats)
        stats["cache_hit"] = 1
        return cached_df.copy(), cached_used_date, stats, list(cached_logs)

    backtrack_logs: list[str] = []

    market_cap_df, fundamental_df, used_date = get_market_data_with_fallback(
        market=normalized_market,
        base_date=base_date,
        backtrack_logs=backtrack_logs,
    )

    result_df = market_cap_df.join(fundamental_df, how="inner")
    total_count = len(result_df)

    result_df = result_df[
        (result_df["PER"] > 0)
        & (result_df["PBR"] > 0)
        & (result_df["시가총액"] >= cap_min)
        & (result_df["시가총액"] <= cap_max)
    ]

    if per_max is not None:
        result_df = result_df[result_df["PER"] <= per_max]

    if pbr_max is not None:
        result_df = result_df[result_df["PBR"] <= pbr_max]

    if normalized_div_policy == "exclude":
        result_df = result_df[result_df["DIV"].notna()]

    filtered_count = len(result_df)

    result_df = add_ticker_names(result_df)
    result_df["PER 기여"] = (1 / result_df["PER"]).where(result_df["PER"] > 0, 0.0)
    result_df["PBR 기여"] = (1 / result_df["PBR"]).where(result_df["PBR"] > 0, 0.0)
    result_df["DIV 기여"] = (result_df["DIV"] / 100).where(result_df["DIV"].notna(), 0.0)
    result_df["TAT"] = result_df["PER 기여"] + result_df["PBR 기여"] + result_df["DIV 기여"]

    result_df = result_df.sort_values("TAT", ascending=False).head(top_n)

    display_df = result_df[
        ["종목명", "시가총액", "PER", "PBR", "DIV", "PER 기여", "PBR 기여", "DIV 기여", "TAT"]
    ].copy()
    display_df["시가총액(조)"] = (display_df["시가총액"] / 1_000_000_000_000).round(3)
    display_df = display_df.drop(columns=["시가총액"])
    display_df["TAT"] = display_df["TAT"].round(4)
    for col in ("PER 기여", "PBR 기여", "DIV 기여"):
        display_df[col] = display_df[col].round(4)

    stats = {
        "total": total_count,
        "filtered": filtered_count,
        "final": len(display_df),
        "cache_hit": 0,
    }

    _QUERY_CACHE[cache_key] = (display_df.copy(), used_date, dict(stats), list(backtrack_logs))

    return display_df, used_date, stats, backtrack_logs
