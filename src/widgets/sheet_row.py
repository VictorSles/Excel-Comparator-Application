"""
SheetRow — uma linha de configuração de sheet dentro de um FilePanel.
Contém: [sheet dropdown] [key dropdown] [≡ pick cols] [× remove]
"""

from typing import Callable, Optional
import customtkinter as ctk
import pandas as pd
from src.constants import (
    SURFACE, BORDER, BORDER_HI, BG3,
    CYAN, CYAN_DIM, RED, TEXT, TEXT_MED, TEXT_DIM, F,
)
from src.widgets.col_picker import ColPicker


class SheetRow(ctk.CTkFrame):
    """Linha compacta de configuração de uma sheet."""

    def __init__(
        self,
        master,
        sheet_names: list[str],
        color: str,
        on_remove: Optional[Callable] = None,
        **kw,
    ):
        super().__init__(master, fg_color=SURFACE, border_color=BORDER, border_width=1, **kw)
        self._sheet_names = sheet_names
        self._color       = color
        self._on_remove   = on_remove
        self._sel_cols: list[str] = []
        self._df_map: dict[str, pd.DataFrame] = {}
        self._build()

    # ── UI ────────────────────────────────────────────────────

    def _build(self) -> None:
        row = ctk.CTkFrame(self, fg_color=SURFACE)
        row.pack(fill="x", padx=6, pady=4)

        # Sheet selector
        ctk.CTkLabel(row, text="Sheet:", font=(F, 8), text_color=TEXT_MED, fg_color=SURFACE).pack(side="left")
        self._sheet_var = ctk.StringVar(value=self._sheet_names[0] if self._sheet_names else "—")
        self._sheet_cb  = ctk.CTkComboBox(
            row, variable=self._sheet_var, values=self._sheet_names,
            width=120, font=(F, 8), fg_color=BG3, border_color=BORDER,
            text_color=TEXT, button_color=BORDER, dropdown_fg_color=BG3,
            command=lambda _: self._on_sheet_change(),
        )
        self._sheet_cb.pack(side="left", padx=(3, 10))

        # Key column selector
        ctk.CTkLabel(row, text="Chave:", font=(F, 8), text_color=TEXT_MED, fg_color=SURFACE).pack(side="left")
        self._key_var = ctk.StringVar(value="—")
        self._key_cb  = ctk.CTkComboBox(
            row, variable=self._key_var, values=["—"],
            width=120, font=(F, 8), fg_color=BG3, border_color=BORDER,
            text_color=TEXT, button_color=BORDER, dropdown_fg_color=BG3,
        )
        self._key_cb.pack(side="left", padx=(3, 8))

        # Return cols label + picker button
        self._sel_lbl_var = ctk.StringVar(value="(todas)")
        ctk.CTkLabel(row, textvariable=self._sel_lbl_var, font=(F, 7),
                     text_color=TEXT_DIM, fg_color=SURFACE).pack(side="left")
        self._pick_btn = ctk.CTkButton(
            row, text="≡", width=28, height=22,
            fg_color=BG3, hover_color=BORDER_HI,
            text_color=CYAN, font=(F, 9, "bold"),
            command=self._pick_cols,
        )
        self._pick_btn.pack(side="left", padx=(4, 0))

        # Remove button
        ctk.CTkButton(
            row, text="×", width=24, height=22,
            fg_color="transparent", hover_color="#2a0010",
            text_color=RED, font=(F, 11, "bold"),
            command=self._remove,
        ).pack(side="right")

        # Color accent left stripe
        ctk.CTkFrame(self, width=3, fg_color=self._color, corner_radius=0).place(x=0, y=0, relheight=1)

    # ── Data ──────────────────────────────────────────────────

    def set_df_map(self, df_map: dict[str, pd.DataFrame]) -> None:
        """Chamado pelo pai após as sheets serem carregadas."""
        self._df_map = df_map
        names = list(df_map.keys())
        self._sheet_cb.configure(values=names)
        if names:
            self._sheet_var.set(names[0])
        self._on_sheet_change()

    def _on_sheet_change(self, *_) -> None:
        name = self._sheet_var.get()
        df   = self._df_map.get(name)
        if df is None:
            return
        cols = list(df.columns)
        self._key_cb.configure(values=cols)
        if cols:
            self._key_var.set(cols[0])
        self._sel_cols = []
        self._sel_lbl_var.set("(todas)")

    def _pick_cols(self) -> None:
        name = self._sheet_var.get()
        df   = self._df_map.get(name)
        if df is None:
            return
        ColPicker(self, list(df.columns), self._sel_cols, self._set_cols)

    def _set_cols(self, cols: list[str]) -> None:
        self._sel_cols = cols
        if cols:
            preview = ", ".join(cols[:2]) + (f" +{len(cols)-2}" if len(cols) > 2 else "")
            self._sel_lbl_var.set(preview)
        else:
            self._sel_lbl_var.set("(todas)")

    def _remove(self) -> None:
        if self._on_remove:
            self._on_remove(self)

    # ── State ─────────────────────────────────────────────────

    def is_ready(self) -> bool:
        v = self._key_var.get()
        return bool(v) and v != "—" and self._sheet_var.get() in self._df_map

    def get_config(self) -> dict:
        name = self._sheet_var.get()
        df   = self._df_map.get(name)
        return {
            "sheet_name": name,
            "df":         df,
            "key":        self._key_var.get(),
            "cols":       self._sel_cols or (list(df.columns) if df is not None else []),
        }
