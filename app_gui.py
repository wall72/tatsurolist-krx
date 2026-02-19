from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from krx_value_service import get_tatsuro_small_mid_value_top10

COLUMNS = ("종목명", "시가총액(조)", "PER", "PBR", "DIV", "TAT")


class KrxValueApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tatsuro KRX 중소형 가치주")
        self.geometry("920x560")
        self.minsize(820, 460)

        self.status_var = tk.StringVar(value="시장/날짜를 선택하고 조회 버튼을 누르세요.")
        self.market_var = tk.StringVar(value="KOSPI")
        self.date_var = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self, padding=12)
        top_frame.pack(fill="x")

        title = ttk.Label(
            top_frame,
            text="Tatsuro 제안식 KRX 중소형 가치주 (PER/PBR/DIV 기반)",
            font=("Malgun Gothic", 12, "bold"),
        )
        title.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))

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

        top_frame.columnconfigure(4, weight=1)

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 8))
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", height=16)
        for col in COLUMNS:
            self.tree.heading(col, text=col)
            anchor = "w" if col == "종목명" else "e"
            width = 220 if col == "종목명" else 120
            self.tree.column(col, anchor=anchor, width=width, stretch=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        status = ttk.Label(self, textvariable=self.status_var, padding=(12, 6, 12, 12))
        status.pack(fill="x")

    def fetch_data(self):
        self.fetch_button.config(state="disabled")
        self.status_var.set("데이터 조회 중...")
        threading.Thread(target=self._fetch_data_worker, daemon=True).start()

    def _fetch_data_worker(self):
        try:
            df, used_date = get_tatsuro_small_mid_value_top10(
                market=self.market_var.get(),
                date=self.date_var.get() or None,
            )
            self.after(0, self._render_table, df, used_date)
        except Exception as exc:
            self.after(0, self._show_error, str(exc))

    def _render_table(self, df, used_date: str):
        self.tree.delete(*self.tree.get_children())

        if df.empty:
            self.status_var.set(f"조건에 맞는 데이터가 없습니다. (기준일: {used_date})")
            self.fetch_button.config(state="normal")
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
                    f"{row['TAT']:.4f}",
                ),
            )

        self.status_var.set(
            f"조회 완료: {len(df)}개 종목 | 시장: {self.market_var.get()} | 기준일: {used_date}"
        )
        self.fetch_button.config(state="normal")

    def _show_error(self, message: str):
        self.status_var.set("조회 실패")
        self.fetch_button.config(state="normal")
        messagebox.showerror("오류", f"데이터 조회 중 오류가 발생했습니다.\n\n{message}")


if __name__ == "__main__":
    app = KrxValueApp()
    app.mainloop()
