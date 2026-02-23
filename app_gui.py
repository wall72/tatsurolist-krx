from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from time import perf_counter
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from krx_value_service import get_tatsuro_small_mid_value_top10

DIV_POLICIES = ("zero", "exclude")

COLUMNS = (
    "종목명",
    "시가총액(조)",
    "PER",
    "PBR",
    "DIV",
    "PER 기여",
    "PBR 기여",
    "DIV 기여",
    "TAT",
)
DEFAULT_CAP_MIN_EOK = 5000
DEFAULT_CAP_MAX_EOK = 10000
DEFAULT_TOP_N = 10
DEFAULT_PER_MAX = ""
DEFAULT_PBR_MAX = ""


class KrxValueApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tatsuro KRX 중소형 가치주")
        self.geometry("1160x560")
        self.minsize(980, 460)

        self.status_var = tk.StringVar(value="시장/날짜를 선택하고 조회 버튼을 누르세요.")
        self.market_var = tk.StringVar(value="KOSPI")
        self.date_var = tk.StringVar(value="")
        self.cap_min_var = tk.StringVar(value=str(DEFAULT_CAP_MIN_EOK))
        self.cap_max_var = tk.StringVar(value=str(DEFAULT_CAP_MAX_EOK))
        self.top_n_var = tk.StringVar(value=str(DEFAULT_TOP_N))
        self.per_max_var = tk.StringVar(value=DEFAULT_PER_MAX)
        self.pbr_max_var = tk.StringVar(value=DEFAULT_PBR_MAX)
        self.div_policy_var = tk.StringVar(value="zero")
        self.result_header_var = tk.StringVar(value="결과 헤더: 시장/기준일 정보가 여기에 표시됩니다.")

        self._latest_result_df = None
        self._last_used_date = ""
        self._fetch_started_at = 0.0
        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self, padding=12)
        top_frame.pack(fill="x")

        title = ttk.Label(
            top_frame,
            text="Tatsuro 제안식 KRX 중소형 가치주 (PER/PBR/DIV 기반)",
            font=("Malgun Gothic", 12, "bold"),
        )
        title.grid(row=0, column=0, columnspan=7, sticky="w", pady=(0, 10))

        ttk.Label(top_frame, text="시장").grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.market_combo = ttk.Combobox(
            top_frame,
            textvariable=self.market_var,
            values=("KOSPI", "KOSDAQ"),
            state="readonly",
            width=10,
        )
        self.market_combo.grid(row=1, column=1, sticky="w", padx=(0, 12))

        ttk.Label(top_frame, text="기준일").grid(row=1, column=2, sticky="w", padx=(0, 6))
        self.date_entry = ttk.Entry(top_frame, textvariable=self.date_var, width=14)
        self.date_entry.grid(row=1, column=3, sticky="w", padx=(0, 8))

        ttk.Label(top_frame, text="(YYYYMMDD 또는 YYYY-MM-DD, 비우면 Today)").grid(
            row=1, column=4, sticky="w"
        )

        self.fetch_button = ttk.Button(top_frame, text="목록 조회", command=self.fetch_data)
        self.fetch_button.grid(row=1, column=5, sticky="e", padx=(12, 0))

        self.save_button = ttk.Button(top_frame, text="CSV 저장", command=self.save_csv, state="disabled")
        self.save_button.grid(row=1, column=6, sticky="e", padx=(8, 0))

        ttk.Label(top_frame, text="시총 하한(억원)").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.cap_min_entry = ttk.Entry(top_frame, textvariable=self.cap_min_var, width=12)
        self.cap_min_entry.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(10, 0))

        ttk.Label(top_frame, text="시총 상한(억원)").grid(row=2, column=2, sticky="w", pady=(10, 0))
        self.cap_max_entry = ttk.Entry(top_frame, textvariable=self.cap_max_var, width=12)
        self.cap_max_entry.grid(row=2, column=3, sticky="w", padx=(0, 8), pady=(10, 0))

        ttk.Label(top_frame, text="Top N").grid(row=2, column=4, sticky="w", pady=(10, 0))
        self.top_n_entry = ttk.Entry(top_frame, textvariable=self.top_n_var, width=8)
        self.top_n_entry.grid(row=2, column=4, sticky="e", padx=(0, 100), pady=(10, 0))

        self.reset_button = ttk.Button(top_frame, text="기본값 복원", command=self.reset_defaults)
        self.reset_button.grid(row=2, column=5, sticky="e", padx=(12, 0), pady=(10, 0))

        ttk.Label(top_frame, text="PER 상한(선택)").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.per_max_entry = ttk.Entry(top_frame, textvariable=self.per_max_var, width=12)
        self.per_max_entry.grid(row=3, column=1, sticky="w", padx=(0, 12), pady=(8, 0))

        ttk.Label(top_frame, text="PBR 상한(선택)").grid(row=3, column=2, sticky="w", pady=(8, 0))
        self.pbr_max_entry = ttk.Entry(top_frame, textvariable=self.pbr_max_var, width=12)
        self.pbr_max_entry.grid(row=3, column=3, sticky="w", padx=(0, 8), pady=(8, 0))

        ttk.Label(top_frame, text="DIV 결측 정책").grid(row=3, column=4, sticky="w", pady=(8, 0))
        self.div_policy_combo = ttk.Combobox(
            top_frame,
            textvariable=self.div_policy_var,
            values=DIV_POLICIES,
            state="readonly",
            width=10,
        )
        self.div_policy_combo.grid(row=3, column=4, sticky="e", padx=(0, 60), pady=(8, 0))

        top_frame.columnconfigure(4, weight=1)

        header_label = ttk.Label(self, textvariable=self.result_header_var, padding=(12, 0, 12, 6))
        header_label.pack(fill="x")

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 8))
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col in COLUMNS:
            self.tree.heading(col, text=col)
            anchor = "w" if col == "종목명" else "e"
            width = 220 if col == "종목명" else 95
            self.tree.column(col, anchor=anchor, width=width, stretch=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        status = ttk.Label(self, textvariable=self.status_var, padding=(12, 6, 12, 12))
        status.pack(fill="x")

    def reset_defaults(self):
        self.cap_min_var.set(str(DEFAULT_CAP_MIN_EOK))
        self.cap_max_var.set(str(DEFAULT_CAP_MAX_EOK))
        self.top_n_var.set(str(DEFAULT_TOP_N))
        self.per_max_var.set(DEFAULT_PER_MAX)
        self.pbr_max_var.set(DEFAULT_PBR_MAX)
        self.div_policy_var.set("zero")
        self.status_var.set("기본 파라미터로 복원했습니다.")

    def _validate_inputs(self):
        try:
            cap_min_eok = int(self.cap_min_var.get().strip())
            cap_max_eok = int(self.cap_max_var.get().strip())
            top_n = int(self.top_n_var.get().strip())
        except ValueError as exc:
            raise ValueError("시총 하한/상한과 Top N은 숫자로 입력해야 합니다.") from exc

        if cap_min_eok < 0 or cap_max_eok < 0:
            raise ValueError("시총 하한/상한은 0 이상이어야 합니다.")
        if cap_min_eok > cap_max_eok:
            raise ValueError("시총 하한은 상한보다 클 수 없습니다.")
        if not 1 <= top_n <= 100:
            raise ValueError("Top N은 1~100 범위로 입력해 주세요.")

        per_raw = self.per_max_var.get().strip()
        pbr_raw = self.pbr_max_var.get().strip()
        per_max = None
        pbr_max = None

        if per_raw:
            per_max = float(per_raw)
            if per_max <= 0:
                raise ValueError("PER 상한은 0보다 커야 합니다.")

        if pbr_raw:
            pbr_max = float(pbr_raw)
            if pbr_max <= 0:
                raise ValueError("PBR 상한은 0보다 커야 합니다.")

        return (
            cap_min_eok * 100_000_000,
            cap_max_eok * 100_000_000,
            top_n,
            per_max,
            pbr_max,
            self.div_policy_var.get().strip().lower(),
        )

    def fetch_data(self):
        try:
            self._query_params = self._validate_inputs()
        except ValueError as exc:
            messagebox.showwarning("입력값 확인", str(exc))
            return

        self.fetch_button.config(state="disabled")
        self.reset_button.config(state="disabled")
        self.save_button.config(state="disabled")
        self._fetch_started_at = perf_counter()
        self.status_var.set("데이터 조회 중...")
        threading.Thread(target=self._fetch_data_worker, daemon=True).start()

    def _fetch_data_worker(self):
        try:
            cap_min, cap_max, top_n, per_max, pbr_max, div_policy = self._query_params
            df, used_date, stats, logs = get_tatsuro_small_mid_value_top10(
                market=self.market_var.get(),
                date=self.date_var.get() or None,
                cap_min=cap_min,
                cap_max=cap_max,
                top_n=top_n,
                per_max=per_max,
                pbr_max=pbr_max,
                div_policy=div_policy,
            )
            elapsed = perf_counter() - self._fetch_started_at
            self.after(0, self._render_table, df, used_date, stats, logs, elapsed)
        except Exception as exc:
            self.after(0, self._show_error, str(exc))

    def _render_table(self, df, used_date: str, stats: dict[str, int], logs: list[str], elapsed_sec: float):
        self.tree.delete(*self.tree.get_children())
        self._latest_result_df = df.copy()
        self._last_used_date = used_date
        self.result_header_var.set(f"결과 헤더 | 시장: {self.market_var.get()} | 기준일: {used_date}")

        if df.empty:
            cache_text = "캐시사용" if stats.get("cache_hit") else "신규조회"
            self.status_var.set(
                f"조건 통과 종목이 없습니다 | 전체: {stats['total']} | 조건통과: {stats['filtered']} | 최종: 0 | {cache_text} | {elapsed_sec:.2f}s"
            )
            self.fetch_button.config(state="normal")
            self.reset_button.config(state="normal")
            self.save_button.config(state="disabled")
            return

        for _, row in df.iterrows():
            self.tree.insert(
                "",
                "end",
                values=(
                    row["종목명"],
                    f"{row['시가총액(조)']:.3f}",
                    f"{row['PER']:.2f}" if row["PER"] == row["PER"] else "-",
                    f"{row['PBR']:.2f}" if row["PBR"] == row["PBR"] else "-",
                    f"{row['DIV']:.2f}" if row["DIV"] == row["DIV"] else "-",
                    f"{row['PER 기여']:.4f}",
                    f"{row['PBR 기여']:.4f}",
                    f"{row['DIV 기여']:.4f}",
                    f"{row['TAT']:.4f}",
                ),
            )

        cache_text = "캐시사용" if stats.get("cache_hit") else "신규조회"
        backtrack_summary = logs[-1] if logs else "백트래킹 로그 없음"
        self.status_var.set(
            f"조회 완료 | 전체: {stats['total']} | 조건통과: {stats['filtered']} | 최종: {stats['final']} | {cache_text} | {elapsed_sec:.2f}s | {backtrack_summary}"
        )
        self.fetch_button.config(state="normal")
        self.reset_button.config(state="normal")
        self.save_button.config(state="normal")

    def save_csv(self):
        if self._latest_result_df is None or self._latest_result_df.empty:
            messagebox.showwarning("저장 불가", "저장할 결과가 없습니다. 먼저 목록을 조회해 주세요.")
            return

        market = self.market_var.get().strip().upper()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{market}_{self._last_used_date}_{timestamp}.csv"

        file_path = filedialog.asksaveasfilename(
            title="결과 CSV 저장",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")],
        )
        if not file_path:
            self.status_var.set("CSV 저장이 취소되었습니다.")
            return

        try:
            self._latest_result_df.to_csv(file_path, index=False, encoding="utf-8-sig")
            self.status_var.set(f"CSV 저장 완료: {Path(file_path).name}")
            messagebox.showinfo("저장 완료", f"CSV 파일을 저장했습니다.\n\n{file_path}")
        except Exception as exc:
            self.status_var.set("CSV 저장 실패")
            messagebox.showerror("저장 실패", f"CSV 저장 중 오류가 발생했습니다.\n\n{exc}")

    def _show_error(self, message: str):
        self.status_var.set("조회 실패")
        self.fetch_button.config(state="normal")
        self.reset_button.config(state="normal")
        self.save_button.config(state="disabled")
        messagebox.showerror("오류", f"데이터 조회 중 오류가 발생했습니다.\n\n{message}")


if __name__ == "__main__":
    app = KrxValueApp()
    app.mainloop()
