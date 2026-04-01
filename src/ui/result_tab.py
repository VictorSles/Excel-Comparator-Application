"""
ResultTab — uma aba de resultado com Treeview, filtros e detalhe de linha.
"""

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
import pandas as pd

from src.constants import (
    BG, BG2, SURFACE, BORDER, BORDER_HI,
    CYAN, CYAN_DIM, GREEN, RED, AMBER, TEXT, TEXT_MED, WHITE, F,
)


class ResultTab(ctk.CTkFrame):
    """Frame com treeview, filtro textual, filtro match/nomatch e exportação."""

    def __init__(self, master, df: pd.DataFrame, tab_label: str):
        super().__init__(master, fg_color=BG)
        self._df        = df
        self._tab_label = tab_label
        self._build()

    # ── UI ────────────────────────────────────────────────────

    def _build(self) -> None:
        # Stats + filter row
        top = ctk.CTkFrame(self, fg_color=BG)
        top.pack(fill="x", pady=(4, 4))

        self._stats_var = ctk.StringVar(value="—")
        ctk.CTkLabel(top, textvariable=self._stats_var, font=(F, 8),
                     text_color=TEXT_MED, fg_color=BG).pack(side="left")

        ctk.CTkLabel(top, text="⌕", font=(F, 12), text_color=TEXT_MED,
                     fg_color=BG).pack(side="left", padx=(12, 0))
        self._fq = ctk.StringVar()
        ctk.CTkEntry(
            top, textvariable=self._fq, width=170, height=24,
            fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, font=(F, 8), placeholder_text="filtrar...",
        ).pack(side="left", padx=(4, 0))
        self._fq.trace("w", lambda *_: self._apply())

        self._show = ctk.StringVar(value="all")
        for val, lbl, clr in [
            ("all",     "TODOS",      TEXT),
            ("match",   "✔ MATCHES",  GREEN),
            ("nomatch", "✘ AUSENTES", RED),
        ]:
            ctk.CTkRadioButton(
                top, text=lbl, variable=self._show, value=val,
                font=(F, 8), text_color=clr,
                fg_color=CYAN_DIM, hover_color=CYAN,
                command=self._apply,
            ).pack(side="left", padx=(8, 0))

        # Treeview wrapper
        tw    = ctk.CTkFrame(self, fg_color=BORDER, corner_radius=0)
        tw.pack(fill="both", expand=True)
        inner = tk.Frame(tw, bg=BG2)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        self._tree = ttk.Treeview(inner, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(inner, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(inner, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("match",   background="#071a0d", foreground=GREEN)
        self._tree.tag_configure("partial", background="#141000", foreground=AMBER)
        self._tree.tag_configure("nomatch", background="#160507", foreground=RED)
        self._tree.tag_configure("even",    background="#07101a")
        self._tree.bind("<Double-1>", self._row_detail)

        self._apply()

    # ── Filter & render ───────────────────────────────────────

    @staticmethod
    def _hidden(df: pd.DataFrame) -> set[str]:
        return {c for c in df.columns if c.startswith("__")}

    def _apply(self) -> None:
        if self._df is None:
            return
        df   = self._df.copy()
        show = self._show.get()
        if show == "match"   and "__match_any__" in df.columns: df = df[df["__match_any__"]]
        elif show == "nomatch" and "__match_any__" in df.columns: df = df[~df["__match_any__"]]

        q = self._fq.get().strip().lower()
        if q:
            hide = self._hidden(df)
            vis  = [c for c in df.columns if c not in hide]
            mask = df[vis].apply(
                lambda row: row.astype(str).str.lower().str.contains(q).any(), axis=1
            )
            df = df[mask]
        self._render(df)

    def _render(self, df: pd.DataFrame) -> None:
        self._tree.delete(*self._tree.get_children())
        if df is None or df.empty:
            self._stats_var.set("Sem resultados")
            return

        hide  = self._hidden(df)
        vcols = [c for c in df.columns if c not in hide]
        mcols = [c for c in df.columns if c.startswith("__match_ref")]

        self._tree["columns"] = vcols
        for c in vcols:
            self._tree.heading(c, text=c, anchor="w")
            mx = max(len(str(c)), df[c].astype(str).str.len().max() if len(df) else len(c))
            self._tree.column(c, width=max(70, min(230, int(mx * 7 + 16))), minwidth=50)

        for i, (_, row) in enumerate(df.iterrows()):
            vals = [str(row[c]) if pd.notna(row.get(c)) else "" for c in vcols]
            if mcols:
                n   = sum(bool(row.get(mc, False)) for mc in mcols)
                tag = "match" if n == len(mcols) else ("partial" if n else "nomatch")
            elif "__match_any__" in row.index:
                tag = "match" if row["__match_any__"] else "nomatch"
            else:
                tag = "even" if i % 2 else ""
            self._tree.insert("", "end", values=vals, tags=(tag,))

        if "__match_any__" in self._df.columns:
            n   = len(self._df)
            nm  = int(self._df["__match_any__"].sum())
            pct = nm / n * 100 if n else 0
            self._stats_var.set(
                f"{n:,} total  ·  {nm:,} matches ({pct:.1f}%)  ·  {n-nm:,} ausentes"
            )
        else:
            self._stats_var.set(f"{len(df):,} linhas")

    # ── Row detail popup ──────────────────────────────────────

    def _row_detail(self, _) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0], "values")
        cols = self._tree["columns"]

        win = ctk.CTkToplevel(self)
        win.title("Row Detail")
        win.configure(fg_color=BG)
        win.geometry("460x480")
        win.grab_set()

        ctk.CTkLabel(win, text="◈  ROW DETAIL", font=(F, 11, "bold"),
                     text_color=CYAN, fg_color=BG).pack(padx=16, pady=(12, 6))
        sf = ctk.CTkScrollableFrame(win, fg_color="#0d1830", border_color=BORDER,
                                     border_width=1, width=420, height=380)
        sf.pack(padx=16, pady=4)
        for c, v in zip(cols, vals):
            r = ctk.CTkFrame(sf, fg_color="#0d1830")
            r.pack(fill="x", padx=4, pady=2)
            ctk.CTkLabel(r, text=f"{c}:", width=160, font=(F, 8, "bold"),
                         text_color=TEXT_MED, fg_color="#0d1830", anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=str(v), font=(F, 9),
                         text_color=WHITE, fg_color="#0d1830", anchor="w").pack(side="left")
        ctk.CTkButton(win, text="FECHAR", width=100, height=28,
                       fg_color=SURFACE, hover_color=BORDER_HI,
                       text_color=CYAN, font=(F, 8),
                       command=win.destroy).pack(pady=8)

    # ── Export ────────────────────────────────────────────────

    def get_export_df(self, mode: str = "all") -> pd.DataFrame:
        if self._df is None:
            return pd.DataFrame()
        df   = self._df.copy()
        hide = self._hidden(df)
        if mode == "match"   and "__match_any__" in df.columns: df = df[df["__match_any__"]]
        elif mode == "nomatch" and "__match_any__" in df.columns: df = df[~df["__match_any__"]]
        return df.drop(columns=[c for c in hide if c in df.columns])
