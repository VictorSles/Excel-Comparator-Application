"""
ResultsPanel — painel de resultados com abas por par de comparação.
"""

import customtkinter as ctk
import pandas as pd
from tkinter import filedialog, messagebox

from src.constants import (
    BG, BG3, CARD, SURFACE, BORDER, BORDER_HI,
    CYAN, CYAN_DIM, GREEN, RED, TEXT, TEXT_MED, WHITE, F,
)
from src.ui.result_tab import ResultTab


class ResultsPanel(ctk.CTkFrame):
    """Painel tabbed: uma aba por comparação base × referência."""

    _PLACEHOLDER = "— aguardando —"

    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self._tabs: dict[str, ResultTab]          = {}
        self._results: dict[str, pd.DataFrame]    = {}
        self._build()

    # ── UI ────────────────────────────────────────────────────

    def _build(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=BG)
        hdr.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(hdr, text="◈  RESULTS", font=(F, 10, "bold"),
                     text_color=CYAN, fg_color=BG).pack(side="left")
        self._total_var = ctk.StringVar(value="—")
        ctk.CTkLabel(hdr, textvariable=self._total_var, font=(F, 8),
                     text_color=TEXT_MED, fg_color=BG).pack(side="left", padx=12)

        # Export buttons
        for lbl, fg, mode, bw in [
            ("⬇ EXPORTAR TUDO (multi-sheet)", WHITE,  "all",     230),
            ("⬇ SÓ MATCHES",                  GREEN,  "match",   120),
            ("⬇ SÓ AUSENTES",                 RED,    "nomatch", 120),
        ]:
            ctk.CTkButton(
                hdr, text=lbl, width=bw, height=26,
                fg_color=SURFACE, hover_color=BORDER_HI,
                text_color=fg, font=(F, 8, "bold"),
                border_color=BORDER, border_width=1,
                command=lambda m=mode: self._export(m),
            ).pack(side="right", padx=(0, 5))

        # Tab view
        self._tabview = ctk.CTkTabview(
            self, fg_color=CARD,
            segmented_button_fg_color=BG3,
            segmented_button_selected_color=CYAN_DIM,
            segmented_button_selected_hover_color=CYAN,
            segmented_button_unselected_color=BG3,
            segmented_button_unselected_hover_color=BORDER_HI,
            text_color=TEXT,
            text_color_disabled=TEXT_MED,
            border_color=BORDER, border_width=1,
        )
        self._tabview.pack(fill="both", expand=True)

        # Placeholder tab
        self._tabview.add(self._PLACEHOLDER)
        ctk.CTkLabel(
            self._tabview.tab(self._PLACEHOLDER),
            text="Execute uma comparação para ver os resultados aqui",
            font=(F, 9), text_color=TEXT_MED, fg_color=CARD,
        ).pack(expand=True, fill="both", pady=40)

    # ── Data ──────────────────────────────────────────────────

    def display_all(self, results: dict[str, pd.DataFrame]) -> None:
        self._results = results

        # Limpa placeholder e abas antigas
        for name in list(self._tabs.keys()):
            try: self._tabview.delete(name)
            except Exception: pass
        self._tabs.clear()
        try: self._tabview.delete(self._PLACEHOLDER)
        except Exception: pass

        total_rows    = sum(len(df) for df in results.values())
        total_matches = sum(
            int(df["__match_any__"].sum()) if "__match_any__" in df.columns else 0
            for df in results.values()
        )
        pct = total_matches / total_rows * 100 if total_rows else 0
        self._total_var.set(
            f"{len(results)} comparações  ·  {total_rows:,} rows  ·  "
            f"{total_matches:,} matches ({pct:.1f}%)"
        )

        for label, df in results.items():
            tab_name = label[:28] + "…" if len(label) > 28 else label
            base, suffix = tab_name, 1
            while tab_name in self._tabs:
                tab_name = f"{base[:25]}_{suffix}"
                suffix  += 1

            self._tabview.add(tab_name)
            rt = ResultTab(self._tabview.tab(tab_name), df, label)
            rt.pack(fill="both", expand=True)
            self._tabs[tab_name] = rt

        if self._tabs:
            try: self._tabview.set(next(iter(self._tabs)))
            except Exception: pass

    # ── Export ────────────────────────────────────────────────

    def _export(self, mode: str) -> None:
        if not self._results:
            messagebox.showwarning("Nada a exportar", "Execute uma comparação primeiro.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"xlookup_export_{mode}.xlsx",
        )
        if not path:
            return
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for tab_name, rt in self._tabs.items():
                    df = rt.get_export_df(mode)
                    if df.empty:
                        continue
                    safe_name = tab_name.replace("/", "_").replace("\\", "_")[:31]
                    df.to_excel(writer, sheet_name=safe_name, index=False)
            messagebox.showinfo(
                "✔ Exportado!",
                f"Excel multi-sheet salvo em:\n{path}\n\n{len(self._tabs)} sheets exportadas.",
            )
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
