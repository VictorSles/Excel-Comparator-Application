"""
ColPicker — janela modal para seleção de colunas de retorno.
"""

from typing import Callable
import customtkinter as ctk
from src.constants import (
    BG, SURFACE, BORDER, BORDER_HI, CYAN, CYAN_DIM, TEXT, TEXT_MED, WHITE, F
)


class ColPicker(ctk.CTkToplevel):
    """Toplevel com checkboxes filtráveis para escolha de colunas."""

    def __init__(
        self,
        master,
        columns: list[str],
        current: list[str],
        callback: Callable[[list[str]], None],
    ):
        super().__init__(master)
        self.title("Column Selector")
        self.configure(fg_color=BG)
        self.resizable(False, False)
        self.grab_set()

        self._cols = columns
        self._current = set(current)
        self._callback = callback
        self._vars: dict[str, ctk.BooleanVar] = {}
        self._build()

    # ── UI ────────────────────────────────────────────────────

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="◈  SELECT RETURN COLUMNS",
            font=(F, 11, "bold"), text_color=CYAN, fg_color=BG,
        ).pack(padx=16, pady=(12, 6))

        # Search bar
        sf = ctk.CTkFrame(self, fg_color=BG)
        sf.pack(fill="x", padx=16, pady=(0, 6))
        ctk.CTkLabel(sf, text="⌕", font=(F, 12), text_color=TEXT_MED, fg_color=BG).pack(side="left")
        self._q = ctk.StringVar()
        ctk.CTkEntry(
            sf, textvariable=self._q, width=250,
            fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, font=(F, 9), placeholder_text="filtrar...",
        ).pack(side="left", padx=(6, 0))
        self._q.trace("w", lambda *_: self._filter())

        # Scrollable checkboxes
        self._scroll = ctk.CTkScrollableFrame(
            self, width=310, height=300,
            fg_color="#0d1830", border_color=BORDER, border_width=1,
        )
        self._scroll.pack(padx=16, pady=4)

        # Quick select
        qs = ctk.CTkFrame(self, fg_color=BG)
        qs.pack(fill="x", padx=16, pady=(4, 2))
        ctk.CTkButton(
            qs, text="■ Todas", width=75, height=24,
            fg_color=SURFACE, hover_color=BORDER_HI,
            text_color=CYAN, font=(F, 8), command=self._all,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            qs, text="□ Nenhuma", width=85, height=24,
            fg_color=SURFACE, hover_color=BORDER_HI,
            text_color=TEXT_MED, font=(F, 8), command=self._none,
        ).pack(side="left")

        # Confirm / Cancel
        br = ctk.CTkFrame(self, fg_color=BG)
        br.pack(pady=8)
        ctk.CTkButton(
            br, text="✔  CONFIRMAR", width=140, height=32,
            fg_color=CYAN_DIM, hover_color=CYAN,
            text_color=WHITE, font=(F, 9, "bold"),
            border_color=CYAN, border_width=1,
            command=self._confirm,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            br, text="CANCELAR", width=100, height=32,
            fg_color=SURFACE, hover_color=BORDER_HI,
            text_color=TEXT_MED, font=(F, 8),
            command=self.destroy,
        ).pack(side="left", padx=6)

        self._populate(self._cols)

    def _populate(self, cols: list[str]) -> None:
        for w in self._scroll.winfo_children():
            w.destroy()
        for col in cols:
            if col not in self._vars:
                self._vars[col] = ctk.BooleanVar(
                    value=(col in self._current if self._current else True)
                )
            ctk.CTkCheckBox(
                self._scroll, text=col, variable=self._vars[col],
                font=(F, 9), text_color=TEXT,
                fg_color=CYAN_DIM, hover_color=CYAN,
                checkmark_color=WHITE, border_color=BORDER,
            ).pack(anchor="w", padx=4, pady=2)

    # ── Actions ───────────────────────────────────────────────

    def _filter(self) -> None:
        q = self._q.get().lower()
        self._populate([c for c in self._cols if q in c.lower()] if q else self._cols)

    def _all(self) -> None:
        for v in self._vars.values():
            v.set(True)

    def _none(self) -> None:
        for v in self._vars.values():
            v.set(False)

    def _confirm(self) -> None:
        self._callback([c for c, v in self._vars.items() if v.get()])
        self.destroy()
