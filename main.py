import queue
import threading

import customtkinter as ctk
from tkinter import messagebox

from src.constants import (
    BG, BG3, CARD, SURFACE, BORDER, BORDER_HI,
    CYAN, CYAN_DIM, MAGENTA, MAG_DIM,
    GREEN, RED, AMBER,
    TEXT, TEXT_DIM, WHITE, F, REF_COLORS,
)
from src.styles import apply_tree_style
from src.widgets.glow_title import GlowTitle
from src.widgets.file_panel import FilePanel
from src.ui.results_panel import ResultsPanel
from src.core.comparator import run_compare

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("XLOOKUP ENGINE  v3.0")
        self.configure(fg_color=BG)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w  = min(1300, sw - 40)
        h  = min(900,  sh - 60)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(960, 620)

        apply_tree_style()
        self._q         = queue.Queue()
        self.ref_panels: list[FilePanel] = []
        self._ref_idx   = 0
        self._comparing = False

        self._build()
        self._poll()
        self.bind("<Control-Return>",   lambda _: self._run())
        self.bind("<Control-KP_Enter>", lambda _: self._run())

    # ── UI BUILD ─────────────────────────────────────────────

    def _build(self) -> None:
        self._build_titlebar()
        ctk.CTkFrame(self, height=1, fg_color=CYAN, corner_radius=0).pack(fill="x")
        self._build_body()
        self._build_statusbar()
        self._add_ref()

    def _build_titlebar(self) -> None:
        tb = ctk.CTkFrame(self, height=44, fg_color=BG3, corner_radius=0)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        GlowTitle(tb, text="◈  XLOOKUP  ENGINE").pack(side="left", padx=12, pady=6)
        ctk.CTkLabel(
            tb, text="v3.0  ·  multi-sheet  ·  multi-ref  ·  async I/O  ·  Ctrl+Enter to run",
            font=(F, 7), text_color=TEXT_DIM, fg_color=BG3,
        ).pack(side="left", padx=(0, 20))

        self._hdr_var = ctk.StringVar(value="● aguardando...")
        self._hdr_lbl = ctk.CTkLabel(tb, textvariable=self._hdr_var,
                                      font=(F, 8), text_color=TEXT_DIM, fg_color=BG3)
        self._hdr_lbl.pack(side="right", padx=14)

    def _build_body(self) -> None:
        outer = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        outer.pack(fill="both", expand=True, padx=10, pady=6)

        # ── Files row
        files_row = ctk.CTkFrame(outer, fg_color=BG)
        files_row.pack(fill="x", pady=(0, 5))

        # BASE column
        base_col = ctk.CTkFrame(files_row, fg_color=BG, width=380)
        base_col.pack(side="left", fill="y", padx=(0, 8))
        base_col.pack_propagate(False)
        bh = ctk.CTkFrame(base_col, fg_color=BG)
        bh.pack(fill="x", pady=(0, 3))
        ctk.CTkLabel(bh, text="[ BASE FILE ]", font=(F, 8, "bold"),
                     text_color=CYAN, fg_color=BG).pack(side="left")
        ctk.CTkLabel(bh, text="arquivo de origem", font=(F, 7),
                     text_color=TEXT_DIM, fg_color=BG).pack(side="left", padx=6)
        self.base_panel = FilePanel(base_col, label="BASE", color=CYAN,
                                     app_queue=self._q, on_ready=self._file_ready)
        self.base_panel.hide_x()
        self.base_panel.pack(fill="both", expand=True)

        # REFS column
        refs_col = ctk.CTkFrame(files_row, fg_color=BG)
        refs_col.pack(side="left", fill="both", expand=True)
        rh = ctk.CTkFrame(refs_col, fg_color=BG)
        rh.pack(fill="x", pady=(0, 3))
        ctk.CTkLabel(rh, text="[ REFERENCE FILES ]", font=(F, 8, "bold"),
                     text_color=MAGENTA, fg_color=BG).pack(side="left")
        ctk.CTkLabel(rh, text="N arquivos · N sheets cada", font=(F, 7),
                     text_color=TEXT_DIM, fg_color=BG).pack(side="left", padx=6)
        ctk.CTkButton(
            rh, text="  +  ADICIONAR  ", width=130, height=24,
            fg_color=MAG_DIM, hover_color=MAGENTA,
            text_color=WHITE, font=(F, 8, "bold"),
            border_color=MAGENTA, border_width=1,
            command=self._add_ref,
        ).pack(side="right")

        self._refs_scroll = ctk.CTkScrollableFrame(
            refs_col, fg_color=BG3, border_color=BORDER, border_width=1, height=185,
        )
        self._refs_scroll.pack(fill="both", expand=True)
        self._ref_ph = ctk.CTkLabel(
            self._refs_scroll,
            text="Clique em  +  ADICIONAR  para incluir arquivos de referência",
            font=(F, 9), text_color=TEXT_DIM, fg_color=BG3,
        )
        self._ref_ph.pack(pady=28)

        # ── Options + Run
        opts = ctk.CTkFrame(outer, fg_color=CARD, border_color=BORDER, border_width=1)
        opts.pack(fill="x", pady=(0, 5))
        row = ctk.CTkFrame(opts, fg_color=CARD)
        row.pack(fill="x", padx=10, pady=7)

        ctk.CTkLabel(row, text="JOIN:", font=(F, 8),
                     text_color=TEXT_DIM, fg_color=CARD).pack(side="left", padx=(0, 4))
        self._join = ctk.StringVar(value="left")
        for val, lbl in [("left","LEFT"), ("inner","INNER"), ("outer","OUTER"), ("right","RIGHT")]:
            ctk.CTkRadioButton(
                row, text=lbl, variable=self._join, value=val,
                font=(F, 8), text_color=WHITE,
                fg_color=CYAN_DIM, hover_color=CYAN,
            ).pack(side="left", padx=4)

        ctk.CTkFrame(row, width=1, fg_color=BORDER).pack(side="left", fill="y", padx=8)
        self._case  = ctk.BooleanVar(value=False)
        self._strip = ctk.BooleanVar(value=True)
        for var, lbl in [(self._case, "Case-insensitive"), (self._strip, "Strip espaços")]:
            ctk.CTkCheckBox(
                row, text=lbl, variable=var,
                font=(F, 8), text_color=WHITE,
                fg_color=CYAN_DIM, hover_color=CYAN, checkmark_color=WHITE,
            ).pack(side="left", padx=6)

        ctk.CTkFrame(row, width=1, fg_color=BORDER).pack(side="left", fill="y", padx=8)

        self._run_btn = ctk.CTkButton(
            row, text="▶  EXECUTAR", width=155, height=34,
            fg_color=CYAN_DIM, hover_color=CYAN,
            text_color=WHITE, font=(F, 10, "bold"),
            border_color=CYAN, border_width=1,
            command=self._run,
        )
        self._run_btn.pack(side="left", padx=(0, 8))

        self._prog = ctk.CTkProgressBar(
            row, width=120, height=7, fg_color=BG3,
            progress_color=CYAN, mode="indeterminate",
        )
        self._run_lbl_var = ctk.StringVar(value="Ctrl+Enter para executar")
        self._run_lbl = ctk.CTkLabel(row, textvariable=self._run_lbl_var,
                                      font=(F, 8), text_color=TEXT_DIM, fg_color=CARD)
        self._run_lbl.pack(side="left")

        # ── Results
        self._results = ResultsPanel(outer)
        self._results.pack(fill="both", expand=True)

    def _build_statusbar(self) -> None:
        ctk.CTkFrame(self, height=1, fg_color=BORDER, corner_radius=0).pack(fill="x")
        sb = ctk.CTkFrame(self, height=20, fg_color=BG3, corner_radius=0)
        sb.pack(fill="x")
        sb.pack_propagate(False)
        ctk.CTkLabel(
            sb,
            text="  ◈ XLOOKUP ENGINE v3.0  ·  multi-sheet Excel export  ·  double-click → detail  ·  Ctrl+Enter",
            font=(F, 7), text_color=TEXT_DIM, fg_color=BG3,
        ).pack(side="left")

    # ── Ref management ────────────────────────────────────────

    def _add_ref(self) -> None:
        if self._ref_ph.winfo_ismapped():
            self._ref_ph.pack_forget()
        self._ref_idx += 1
        i       = self._ref_idx
        color   = REF_COLORS[(i - 1) % len(REF_COLORS)]
        label   = f"REF-{i:02d}"
        wrapper = ctk.CTkFrame(self._refs_scroll, fg_color=BG3)
        wrapper.pack(fill="x", padx=4, pady=3)
        panel = FilePanel(wrapper, label=label, color=color,
                          app_queue=self._q, on_ready=self._file_ready)
        panel.pack(fill="x")
        self.ref_panels.append(panel)

        def make_remover(p=panel, w=wrapper):
            def _remove():
                if p in self.ref_panels:
                    self.ref_panels.remove(p)
                w.destroy()
                if not self.ref_panels:
                    self._ref_ph.pack(pady=28)
                self._file_ready()
            return _remove

        panel._remove_cb = make_remover()
        self._refs_scroll.after(
            50, lambda: self._refs_scroll._parent_canvas.yview_moveto(1.0)
        )

    # ── Queue poll ────────────────────────────────────────────

    def _poll(self) -> None:
        try:
            while True:
                msg  = self._q.get_nowait()
                kind = msg[0]
                if kind == "loaded":
                    _, pid, path, sheets, err = msg
                    for p in [self.base_panel] + self.ref_panels:
                        if id(p) == pid:
                            p.receive_load(path, sheets, err)
                            break
                elif kind == "compare_done":
                    self._on_done(msg[1])
                elif kind == "compare_err":
                    self._on_err(msg[1])
        except queue.Empty:
            pass
        self.after(38, self._poll)

    def _file_ready(self) -> None:
        ready = sum(1 for p in [self.base_panel] + self.ref_panels if p.is_ready())
        total = 1 + len(self.ref_panels)
        color = GREEN if ready == total else AMBER
        self._hdr_var.set(f"● {ready}/{total} prontos")
        self._hdr_lbl.configure(text_color=color)

    # ── Compare ───────────────────────────────────────────────

    def _run(self) -> None:
        if self._comparing:
            return
        if not self.base_panel.is_ready():
            messagebox.showwarning("Base file", "Carregue o arquivo BASE primeiro.")
            return
        ready_refs = [p for p in self.ref_panels if p.is_ready()]
        if not ready_refs:
            messagebox.showwarning("Referências", "Carregue ao menos um arquivo de referência.")
            return

        self._comparing = True
        self._run_btn.configure(state="disabled")
        self._prog.pack(side="left", padx=(8, 0))
        self._prog.start()
        self._run_lbl_var.set("  comparando...")
        self._run_lbl.configure(text_color=AMBER)

        threading.Thread(
            target=run_compare,
            args=(
                self.base_panel,
                ready_refs,
                self._join.get(),
                self._case.get(),
                self._strip.get(),
                self._q,
            ),
            daemon=True,
        ).start()

    def _on_done(self, results: dict) -> None:
        self._comparing = False
        self._prog.stop()
        self._prog.pack_forget()
        self._run_btn.configure(state="normal")

        total   = sum(len(df) for df in results.values())
        matches = sum(
            int(df["__match_any__"].sum()) if "__match_any__" in df.columns else 0
            for df in results.values()
        )
        pct = matches / total * 100 if total else 0
        self._run_lbl_var.set(
            f"  ✔  {len(results)} tabs  ·  {total:,} rows  ·  {matches:,} matches ({pct:.1f}%)"
        )
        self._run_lbl.configure(text_color=GREEN)
        self._hdr_var.set(f"● concluído  ·  {len(results)} comparações")
        self._hdr_lbl.configure(text_color=GREEN)
        self._results.display_all(results)

    def _on_err(self, err: str) -> None:
        self._comparing = False
        self._prog.stop()
        self._prog.pack_forget()
        self._run_btn.configure(state="normal")
        self._run_lbl_var.set("  ✘  erro na comparação")
        self._run_lbl.configure(text_color=RED)
        messagebox.showerror("Erro na comparação", err)


if __name__ == "__main__":
    app = App()
    app.mainloop()
