from __future__ import annotations

import argparse

from krx_backtest import BacktestConfig, create_market_comparison_report, write_backtest_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KRX 월간 리밸런싱 백테스트 실행")
    parser.add_argument("--start-date", required=True, help="시작일 (YYYYMMDD 또는 YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="종료일 (YYYYMMDD 또는 YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--cap-min", type=int, default=500_000_000_000)
    parser.add_argument("--cap-max", type=int, default=1_000_000_000_000)
    parser.add_argument("--per-max", type=float, default=None)
    parser.add_argument("--pbr-max", type=float, default=None)
    parser.add_argument("--div-policy", choices=("zero", "exclude"), default="zero")
    parser.add_argument("--output-dir", default="reports")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = BacktestConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        top_n=args.top_n,
        cap_min=args.cap_min,
        cap_max=args.cap_max,
        per_max=args.per_max,
        pbr_max=args.pbr_max,
        div_policy=args.div_policy,
    )

    summary_df, market_results = create_market_comparison_report(config=config)
    report_path = write_backtest_report(args.output_dir, summary_df, market_results)

    print("[완료] 백테스트 리포트 생성")
    print(f"- report: {report_path}")
    print(f"- summary rows: {len(summary_df)}")


if __name__ == "__main__":
    main()
