"""
FilePanel — painel de carregamento e configuração de arquivo Excel.
Suporta múltiplas SheetRows (N sheets por arquivo).
"""

import os
import queue
import threading
from typing import Callable, Optional

import customtkinter as ctk
import pandas as pd
from tkinter import filedialog

from src.constants import (
    CARD, BG3, BORDER, BORDER_HI,
    AMBER, GREEN, RED, CYAN, TEXT, TEXT_DIM, TEXT_MED, WHITE, F,
)
from src.widgets.pulse_dot import PulseDot
from src.widgets.sheet_row import SheetRow


class FilePanel(ctk.CTkFrame):
    """Painel completo para um arquivo: load, status e seleção de sheets/chaves."""

    _SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(
        self,
        master,
        label: str,
        color: str,
        app_queue: queue.Queue,
        on_ready: Optional[Callable] = None,
        **kw,
    ):
        super().__init__(master, fg_color=CARD, border_color=color, border_width=1, **kw)
        self._label    = label
        self._color    = color
        self._q        = app_queue
        self._on_ready = on_ready
        self._remove_cb: Optional[Callable] = None

        self.filepath: Optional[str] = None
        self.all_sheets: dict[str, pd.DataFrame] = {}
        self._loading   = False
        self._spin_idx  = 0
        self._sheet_rows: list[SheetRow] = []
        self._build()

    # ── UI ────────────────────────────────────────────────────

    def _build(self) -> None:
        # Header
        hdr  = ctk.CTkFrame(self, fg_color=BG3, corner_radius=0)
        hdr.pack(fill="x")
        left = ctk.CTkFrame(hdr, fg_color=BG3)
        left.pack(side="left", padx=6, pady=3)
        self._dot = PulseDot(left, bg_color=BG3)
        self._dot.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(left, text=self._label, font=(F, 9, "bold"),
                     text_color=self._color, fg_color=BG3).pack(side="left")
        right = ctk.CTkFrame(hdr, fg_color=BG3)
        right.pack(side="right", padx=4)
        self._spin_lbl = ctk.CTkLabel(right, text="", width=16,
                                       font=(F, 11), text_color=AMBER, fg_color=BG3)
        self._spin_lbl.pack(side="right", padx=(0, 2))
        self._x_btn = ctk.CTkButton(
            right, text="×", width=22, height=20,
            fg_color="transparent", hover_color="#2a0010",
            text_color=RED, font=(F, 12, "bold"),
            command=self._do_remove,
        )
        self._x_btn.pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=self._color, corner_radius=0).pack(fill="x")

        body = ctk.CTkFrame(self, fg_color=CARD)
        body.pack(fill="x", padx=8, pady=5)

        # File path + load button
        r1 = ctk.CTkFrame(body, fg_color=CARD)
        r1.pack(fill="x", pady=(0, 4))
        self._path_var = ctk.StringVar(value="── nenhum arquivo selecionado ──")
        self._path_lbl = ctk.CTkLabel(
            r1, textvariable=self._path_var,
            font=(F, 8), text_color=TEXT_MED, fg_color=CARD, anchor="w",
        )
        self._path_lbl.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            r1, text="LOAD", width=60, height=24,
            fg_color=self._color, hover_color=BORDER_HI,
            text_color="#030711", font=(F, 8, "bold"),
            command=self._open_dialog,
        ).pack(side="right", padx=(6, 0))

        # Sheet rows container
        self._rows_frame = ctk.CTkScrollableFrame(
            body, fg_color=CARD, height=90, border_color=BORDER, border_width=0,
        )
        self._rows_frame.pack(fill="x", pady=(0, 3))

        self._no_sheets_lbl = ctk.CTkLabel(
            self._rows_frame,
            text="Carregue um arquivo para configurar as sheets",
            font=(F, 8), text_color=TEXT_DIM, fg_color=CARD,
        )
        self._no_sheets_lbl.pack(pady=8)

        # "+ add sheet" button (disabled until file loaded)
        self._add_sheet_btn = ctk.CTkButton(
            body, text="  +  SHEET  ", width=110, height=22,
            fg_color=BORDER, hover_color=BORDER_HI,
            text_color=self._color, font=(F, 8, "bold"),
            border_color=self._color, border_width=1,
            state="disabled", command=self._add_sheet_row,
        )
        self._add_sheet_btn.pack(anchor="w")

        # Info label
        self._info_var = ctk.StringVar(value="")
        ctk.CTkLabel(body, textvariable=self._info_var, font=(F, 7),
                     text_color=TEXT_DIM, fg_color=CARD, anchor="w").pack(anchor="w")

    # ── Helpers ───────────────────────────────────────────────

    def hide_x(self) -> None:
        self._x_btn.pack_forget()

    def _do_remove(self) -> None:
        if self._remove_cb:
            self._remove_cb()

    # ── Async load ────────────────────────────────────────────

    def _open_dialog(self) -> None:
        if self._loading:
            return
        path = filedialog.askopenfilename(
            title=f"Selecionar — {self._label}",
            filetypes=[("Excel", "*.xlsx *.xls *.xlsm"), ("Todos", "*.*")],
        )
        if path:
            self._start_load(path)

    def _start_load(self, path: str) -> None:
        self._loading = True
        name = os.path.basename(path)
        self._path_var.set(name[:44] + "…" if len(name) > 44 else name)
        self._path_lbl.configure(text_color=AMBER)
        self._dot.set_state("loading")
        self._spin_anim()
        threading.Thread(target=self._read, args=(path,), daemon=True).start()

    def _spin_anim(self) -> None:
        if not self._loading:
            self._spin_lbl.configure(text="")
            return
        self._spin_lbl.configure(text=self._SPIN[self._spin_idx % len(self._SPIN)])
        self._spin_idx += 1
        self.after(80, self._spin_anim)

    def _read(self, path: str) -> None:
        try:
            sheets = pd.read_excel(path, sheet_name=None)
            self._q.put(("loaded", id(self), path, sheets, None))
        except Exception as e:
            self._q.put(("loaded", id(self), path, None, str(e)))

    def receive_load(self, path: str, sheets: Optional[dict], error: Optional[str]) -> None:
        self._loading = False
        self._spin_lbl.configure(text="")

        if error:
            self._dot.set_state("error")
            self._path_lbl.configure(text_color=RED)
            self._info_var.set(f"✘  {str(error)[:55]}")
            return

        self.filepath   = path
        self.all_sheets = sheets
        names = list(sheets.keys())

        for r in self._sheet_rows:
            r.destroy()
        self._sheet_rows.clear()
        if self._no_sheets_lbl.winfo_exists():
            self._no_sheets_lbl.pack_forget()

        self._add_sheet_row()
        self._add_sheet_btn.configure(state="normal")
        self._dot.set_state("ready")
        self._path_lbl.configure(text_color=GREEN)
        total_rows = sum(len(df) for df in sheets.values())
        self._info_var.set(f"✔  {len(names)} sheets  ·  {total_rows:,} rows total")

        if self._on_ready:
            self._on_ready()

    # ── Sheet row management ──────────────────────────────────

    def _add_sheet_row(self) -> None:
        if not self.all_sheets:
            return
        used  = {r._sheet_var.get() for r in self._sheet_rows}
        names = list(self.all_sheets.keys())
        default = next((n for n in names if n not in used), names[0])

        row = SheetRow(self._rows_frame, names, self._color, on_remove=self._remove_sheet_row)
        row.set_df_map(self.all_sheets)
        row._sheet_var.set(default)
        row._on_sheet_change()
        row.pack(fill="x", padx=2, pady=2)
        self._sheet_rows.append(row)

        if self._on_ready:
            self._on_ready()

    def _remove_sheet_row(self, row: SheetRow) -> None:
        if row in self._sheet_rows:
            self._sheet_rows.remove(row)
        row.destroy()
        if not self._sheet_rows:
            self._no_sheets_lbl.pack(pady=8)
        if self._on_ready:
            self._on_ready()

    # ── State & config ────────────────────────────────────────

    def is_ready(self) -> bool:
        return bool(self.all_sheets) and any(r.is_ready() for r in self._sheet_rows)

    def get_configs(self) -> list[dict]:
        """Retorna lista de {sheet_name, df, key, cols} para cada sheet row pronta."""
        return [r.get_config() for r in self._sheet_rows if r.is_ready()]
