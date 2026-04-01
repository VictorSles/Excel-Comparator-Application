"""
╔══════════════════════════════════════════════════════════════════╗
║   XLOOKUP ENGINE v3.0 — Multi-Sheet · Multi-Ref Comparator      ║
║   customtkinter · ZERO tk.Canvas · multi-sheet · tabbed results ║
╚══════════════════════════════════════════════════════════════════╝
  pip install pandas openpyxl customtkinter
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
import pandas as pd
import threading, queue, os, math, itertools

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ══════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════
BG        = "#030711"
BG2       = "#060d1e"
BG3       = "#0a1228"
CARD      = "#0d1830"
SURFACE   = "#111f3a"
BORDER    = "#182840"
BORDER_HI = "#1e3254"

CYAN      = "#00e5ff"
CYAN_DIM  = "#004d6e"
MAGENTA   = "#d500f9"
MAG_DIM   = "#4a0070"
GREEN     = "#00e676"
RED       = "#ff1744"
AMBER     = "#ffab00"

TEXT      = "#a8c0e0"
TEXT_MED  = "#4a6a9a"
TEXT_DIM  = "#1e3060"
WHITE     = "#e8f4ff"

F = "Courier New"
REF_COLORS = [MAGENTA,"#ff6d00","#ffd600","#00e676",
              "#448aff","#ff4081","#b2ff59","#ea80fc"]

# ══════════════════════════════════════════════════════════════
#  TTK TREEVIEW STYLE
# ══════════════════════════════════════════════════════════════
def _tree_style():
    s = ttk.Style()
    try: s.theme_use("clam")
    except: pass
    s.configure("Treeview", background=BG2, foreground=TEXT,
                fieldbackground=BG2, rowheight=22, font=(F,9))
    s.configure("Treeview.Heading", background=BG3, foreground=CYAN,
                font=(F,9,"bold"), relief="flat")
    s.map("Treeview",
          background=[("selected", BORDER_HI)],
          foreground=[("selected", WHITE)])
    s.configure("TScrollbar", background=BG3, troughcolor=BG,
                arrowcolor=CYAN, borderwidth=0, relief="flat")

# ══════════════════════════════════════════════════════════════
#  PULSE DOT — CTkLabel only, no Canvas
# ══════════════════════════════════════════════════════════════
class PulseDot(ctk.CTkLabel):
    _COLORS = {
        "idle":    [TEXT_DIM],
        "ready":   [GREEN],
        "error":   [RED],
        "loading": [AMBER,"#a87000","#ffcc44","#a87000"],
    }
    def __init__(self, master, bg_color=CARD, **kw):
        super().__init__(master, text="●", font=(F,10),
                         text_color=TEXT_DIM, fg_color=bg_color, width=14, **kw)
        self._state="idle"; self._fi=0; self._active=True; self._tick()
    def set_state(self, s): self._state=s; self._fi=0
    def destroy(self): self._active=False; super().destroy()
    def _tick(self):
        if not self._active: return
        frames = self._COLORS.get(self._state,[TEXT_DIM])
        try: self.configure(text_color=frames[self._fi % len(frames)])
        except: pass
        self._fi+=1; self.after(120,self._tick)

# ══════════════════════════════════════════════════════════════
#  GLOW TITLE — CTkLabel only, no Canvas
# ══════════════════════════════════════════════════════════════
class GlowTitle(ctk.CTkLabel):
    _PALETTE = [
        f"#00{int(229*(0.55+0.45*math.sin(i*math.pi*2/16))):02x}"
        f"{int(255*(0.55+0.45*math.sin(i*math.pi*2/16))):02x}"
        for i in range(16)
    ]
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text, font=(F,14,"bold"),
                         text_color=CYAN, fg_color=BG3, anchor="w", **kw)
        self._fi=0; self._active=True; self._tick()
    def destroy(self): self._active=False; super().destroy()
    def _tick(self):
        if not self._active: return
        try: self.configure(text_color=self._PALETTE[self._fi%len(self._PALETTE)])
        except: pass
        self._fi+=1; self.after(80,self._tick)

# ══════════════════════════════════════════════════════════════
#  COLUMN PICKER
# ══════════════════════════════════════════════════════════════
class ColPicker(ctk.CTkToplevel):
    def __init__(self, master, columns, current, callback):
        super().__init__(master)
        self.title("Column Selector"); self.configure(fg_color=BG)
        self.resizable(False,False); self.grab_set()
        self._cols=columns; self._current=set(current)
        self._callback=callback; self._vars={}; self._build()

    def _build(self):
        ctk.CTkLabel(self,text="◈  SELECT RETURN COLUMNS",
                     font=(F,11,"bold"),text_color=CYAN,fg_color=BG).pack(padx=16,pady=(12,6))
        sf=ctk.CTkFrame(self,fg_color=BG); sf.pack(fill="x",padx=16,pady=(0,6))
        ctk.CTkLabel(sf,text="⌕",font=(F,12),text_color=TEXT_MED,fg_color=BG).pack(side="left")
        self._q=ctk.StringVar()
        ctk.CTkEntry(sf,textvariable=self._q,width=250,fg_color=SURFACE,
                     border_color=BORDER,text_color=TEXT,font=(F,9),
                     placeholder_text="filtrar...").pack(side="left",padx=(6,0))
        self._q.trace("w",lambda*_:self._filter())
        self._scroll=ctk.CTkScrollableFrame(self,width=310,height=300,
                                             fg_color=CARD,border_color=BORDER,border_width=1)
        self._scroll.pack(padx=16,pady=4)
        qs=ctk.CTkFrame(self,fg_color=BG); qs.pack(fill="x",padx=16,pady=(4,2))
        ctk.CTkButton(qs,text="■ Todas",width=75,height=24,fg_color=SURFACE,
                       hover_color=BORDER_HI,text_color=CYAN,font=(F,8),
                       command=self._all).pack(side="left",padx=(0,6))
        ctk.CTkButton(qs,text="□ Nenhuma",width=85,height=24,fg_color=SURFACE,
                       hover_color=BORDER_HI,text_color=TEXT_MED,font=(F,8),
                       command=self._none).pack(side="left")
        br=ctk.CTkFrame(self,fg_color=BG); br.pack(pady=8)
        ctk.CTkButton(br,text="✔  CONFIRMAR",width=140,height=32,
                       fg_color=CYAN_DIM,hover_color=CYAN,text_color=WHITE,
                       font=(F,9,"bold"),border_color=CYAN,border_width=1,
                       command=self._confirm).pack(side="left",padx=6)
        ctk.CTkButton(br,text="CANCELAR",width=100,height=32,
                       fg_color=SURFACE,hover_color=BORDER_HI,
                       text_color=TEXT_MED,font=(F,8),
                       command=self.destroy).pack(side="left",padx=6)
        self._populate(self._cols)

    def _populate(self,cols):
        for w in self._scroll.winfo_children(): w.destroy()
        for col in cols:
            if col not in self._vars:
                self._vars[col]=ctk.BooleanVar(
                    value=(col in self._current if self._current else True))
            ctk.CTkCheckBox(self._scroll,text=col,variable=self._vars[col],
                             font=(F,9),text_color=TEXT,fg_color=CYAN_DIM,
                             hover_color=CYAN,checkmark_color=WHITE,
                             border_color=BORDER).pack(anchor="w",padx=4,pady=2)

    def _filter(self):
        q=self._q.get().lower()
        self._populate([c for c in self._cols if q in c.lower()] if q else self._cols)
    def _all(self):
        for v in self._vars.values(): v.set(True)
    def _none(self):
        for v in self._vars.values(): v.set(False)
    def _confirm(self):
        self._callback([c for c,v in self._vars.items() if v.get()]); self.destroy()

# ══════════════════════════════════════════════════════════════
#  SHEET ROW — one row per selected sheet inside a FilePanel
# ══════════════════════════════════════════════════════════════
class SheetRow(ctk.CTkFrame):
    """Compact row: [sheet dropdown] [key dropdown] [≡ pick cols] [× remove]"""

    def __init__(self, master, sheet_names, color, on_remove=None, **kw):
        super().__init__(master, fg_color=SURFACE,
                         border_color=BORDER, border_width=1, **kw)
        self._sheet_names = sheet_names
        self._color       = color
        self._on_remove   = on_remove
        self._sel_cols    = []
        self._df_map      = {}     # will be set by parent
        self._build()

    def _build(self):
        row = ctk.CTkFrame(self, fg_color=SURFACE)
        row.pack(fill="x", padx=6, pady=4)

        # Sheet selector
        ctk.CTkLabel(row, text="Sheet:", font=(F,8),
                     text_color=TEXT_MED, fg_color=SURFACE).pack(side="left")
        self._sheet_var = ctk.StringVar(value=self._sheet_names[0] if self._sheet_names else "—")
        self._sheet_cb  = ctk.CTkComboBox(
            row, variable=self._sheet_var, values=self._sheet_names,
            width=120, font=(F,8), fg_color=BG3, border_color=BORDER,
            text_color=TEXT, button_color=BORDER, dropdown_fg_color=BG3,
            command=lambda _: self._on_sheet_change())
        self._sheet_cb.pack(side="left", padx=(3,10))

        # Key column selector
        ctk.CTkLabel(row, text="Chave:", font=(F,8),
                     text_color=TEXT_MED, fg_color=SURFACE).pack(side="left")
        self._key_var = ctk.StringVar(value="—")
        self._key_cb  = ctk.CTkComboBox(
            row, variable=self._key_var, values=["—"],
            width=120, font=(F,8), fg_color=BG3, border_color=BORDER,
            text_color=TEXT, button_color=BORDER, dropdown_fg_color=BG3)
        self._key_cb.pack(side="left", padx=(3,8))

        # Return cols
        self._sel_lbl_var = ctk.StringVar(value="(todas)")
        ctk.CTkLabel(row, textvariable=self._sel_lbl_var, font=(F,7),
                     text_color=TEXT_DIM, fg_color=SURFACE).pack(side="left")
        self._pick_btn = ctk.CTkButton(
            row, text="≡", width=28, height=22,
            fg_color=BG3, hover_color=BORDER_HI,
            text_color=CYAN, font=(F,9,"bold"),
            command=self._pick_cols)
        self._pick_btn.pack(side="left", padx=(4,0))

        # Remove button
        ctk.CTkButton(row, text="×", width=24, height=22,
                       fg_color="transparent", hover_color="#2a0010",
                       text_color=RED, font=(F,11,"bold"),
                       command=self._remove).pack(side="right")

        # Color accent left stripe
        ctk.CTkFrame(self, width=3, fg_color=self._color,
                     corner_radius=0).place(x=0,y=0,relheight=1)

    def set_df_map(self, df_map: dict):
        """Called by parent once sheets are loaded. df_map = {sheet_name: df}"""
        self._df_map = df_map
        names = list(df_map.keys())
        self._sheet_cb.configure(values=names)
        if names:
            self._sheet_var.set(names[0])
        self._on_sheet_change()

    def _on_sheet_change(self, *_):
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

    def _pick_cols(self):
        name = self._sheet_var.get()
        df   = self._df_map.get(name)
        if df is None:
            return
        ColPicker(self, list(df.columns), self._sel_cols, self._set_cols)

    def _set_cols(self, cols):
        self._sel_cols = cols
        if cols:
            prev = ", ".join(cols[:2]) + (f" +{len(cols)-2}" if len(cols)>2 else "")
            self._sel_lbl_var.set(prev)
        else:
            self._sel_lbl_var.set("(todas)")

    def _remove(self):
        if self._on_remove:
            self._on_remove(self)

    def is_ready(self):
        v = self._key_var.get()
        return bool(v) and v != "—" and self._sheet_var.get() in self._df_map

    def get_config(self):
        name = self._sheet_var.get()
        df   = self._df_map.get(name)
        return {
            "sheet_name": name,
            "df":         df,
            "key":        self._key_var.get(),
            "cols":       self._sel_cols or (list(df.columns) if df is not None else []),
        }

# ══════════════════════════════════════════════════════════════
#  FILE PANEL — supports N sheet rows
# ══════════════════════════════════════════════════════════════
class FilePanel(ctk.CTkFrame):
    _SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, master, label, color, app_queue, on_ready=None, **kw):
        super().__init__(master, fg_color=CARD,
                         border_color=color, border_width=1, **kw)
        self._label     = label
        self._color     = color
        self._q         = app_queue
        self._on_ready  = on_ready
        self._remove_cb = None

        self.filepath    = None
        self.all_sheets  = {}      # {name: df}
        self._loading    = False
        self._spin_idx   = 0
        self._sheet_rows: list[SheetRow] = []
        self._build()

    def _build(self):
        # header
        hdr = ctk.CTkFrame(self, fg_color=BG3, corner_radius=0)
        hdr.pack(fill="x")
        left = ctk.CTkFrame(hdr, fg_color=BG3)
        left.pack(side="left", padx=6, pady=3)
        self._dot = PulseDot(left, bg_color=BG3)
        self._dot.pack(side="left", padx=(0,4))
        ctk.CTkLabel(left, text=self._label, font=(F,9,"bold"),
                     text_color=self._color, fg_color=BG3).pack(side="left")
        right = ctk.CTkFrame(hdr, fg_color=BG3)
        right.pack(side="right", padx=4)
        self._spin_lbl = ctk.CTkLabel(right, text="", width=16,
                                       font=(F,11), text_color=AMBER, fg_color=BG3)
        self._spin_lbl.pack(side="right", padx=(0,2))
        self._x_btn = ctk.CTkButton(right, text="×", width=22, height=20,
                                     fg_color="transparent", hover_color="#2a0010",
                                     text_color=RED, font=(F,12,"bold"),
                                     command=self._do_remove)
        self._x_btn.pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=self._color, corner_radius=0).pack(fill="x")

        body = ctk.CTkFrame(self, fg_color=CARD)
        body.pack(fill="x", padx=8, pady=5)

        # file path + load
        r1 = ctk.CTkFrame(body, fg_color=CARD)
        r1.pack(fill="x", pady=(0,4))
        self._path_var = ctk.StringVar(value="── nenhum arquivo selecionado ──")
        self._path_lbl = ctk.CTkLabel(r1, textvariable=self._path_var,
                                       font=(F,8), text_color=TEXT_MED,
                                       fg_color=CARD, anchor="w")
        self._path_lbl.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(r1, text="LOAD", width=60, height=24,
                       fg_color=self._color, hover_color=BORDER_HI,
                       text_color=BG, font=(F,8,"bold"),
                       command=self._open_dialog).pack(side="right", padx=(6,0))

        # sheet rows container (scrollable)
        self._rows_frame = ctk.CTkScrollableFrame(
            body, fg_color=CARD, height=90,
            border_color=BORDER, border_width=0)
        self._rows_frame.pack(fill="x", pady=(0,3))

        self._no_sheets_lbl = ctk.CTkLabel(
            self._rows_frame,
            text="Carregue um arquivo para configurar as sheets",
            font=(F,8), text_color=TEXT_DIM, fg_color=CARD)
        self._no_sheets_lbl.pack(pady=8)

        # "+ add sheet" button (hidden until file loaded)
        self._add_sheet_btn = ctk.CTkButton(
            body, text="  +  SHEET  ", width=110, height=22,
            fg_color=BORDER, hover_color=BORDER_HI,
            text_color=self._color, font=(F,8,"bold"),
            border_color=self._color, border_width=1,
            state="disabled", command=self._add_sheet_row)
        self._add_sheet_btn.pack(anchor="w")

        # info
        self._info_var = ctk.StringVar(value="")
        ctk.CTkLabel(body, textvariable=self._info_var, font=(F,7),
                     text_color=TEXT_DIM, fg_color=CARD, anchor="w").pack(anchor="w")

    # ── helpers ─────────────────────────────────────────────
    def hide_x(self): self._x_btn.pack_forget()
    def _do_remove(self):
        if self._remove_cb: self._remove_cb()

    # ── async load ──────────────────────────────────────────
    def _open_dialog(self):
        if self._loading: return
        path = filedialog.askopenfilename(
            title=f"Selecionar — {self._label}",
            filetypes=[("Excel","*.xlsx *.xls *.xlsm"),("Todos","*.*")])
        if path: self._start_load(path)

    def _start_load(self, path):
        self._loading = True
        name = os.path.basename(path)
        self._path_var.set(name[:44]+"…" if len(name)>44 else name)
        self._path_lbl.configure(text_color=AMBER)
        self._dot.set_state("loading")
        self._spin_anim()
        threading.Thread(target=self._read, args=(path,), daemon=True).start()

    def _spin_anim(self):
        if not self._loading: self._spin_lbl.configure(text=""); return
        self._spin_lbl.configure(text=self._SPIN[self._spin_idx%len(self._SPIN)])
        self._spin_idx+=1; self.after(80,self._spin_anim)

    def _read(self, path):
        try:
            sheets = pd.read_excel(path, sheet_name=None)
            self._q.put(("loaded",id(self),path,sheets,None))
        except Exception as e:
            self._q.put(("loaded",id(self),path,None,str(e)))

    def receive_load(self, path, sheets, error):
        self._loading=False; self._spin_lbl.configure(text="")
        if error:
            self._dot.set_state("error")
            self._path_lbl.configure(text_color=RED)
            self._info_var.set(f"✘  {str(error)[:55]}")
            return
        self.filepath=path; self.all_sheets=sheets
        names=list(sheets.keys())
        # clear existing rows
        for r in self._sheet_rows: r.destroy()
        self._sheet_rows.clear()
        if self._no_sheets_lbl.winfo_exists():
            self._no_sheets_lbl.pack_forget()
        # auto-add first sheet row
        self._add_sheet_row()
        self._add_sheet_btn.configure(state="normal")
        self._dot.set_state("ready")
        self._path_lbl.configure(text_color=GREEN)
        total_rows = sum(len(df) for df in sheets.values())
        self._info_var.set(
            f"✔  {len(names)} sheets  ·  {total_rows:,} rows total")
        if self._on_ready: self._on_ready()

    # ── sheet row management ─────────────────────────────────
    def _add_sheet_row(self):
        if not self.all_sheets:
            return
        # default: first unused sheet, or first sheet if all used
        used = {r._sheet_var.get() for r in self._sheet_rows}
        names = list(self.all_sheets.keys())
        default = next((n for n in names if n not in used), names[0])

        row = SheetRow(self._rows_frame, names, self._color,
                       on_remove=self._remove_sheet_row)
        row.set_df_map(self.all_sheets)
        row._sheet_var.set(default)
        row._on_sheet_change()
        row.pack(fill="x", padx=2, pady=2)
        self._sheet_rows.append(row)
        if self._on_ready: self._on_ready()

    def _remove_sheet_row(self, row: SheetRow):
        if row in self._sheet_rows:
            self._sheet_rows.remove(row)
        row.destroy()
        if not self._sheet_rows:
            self._no_sheets_lbl.pack(pady=8)
        if self._on_ready: self._on_ready()

    # ── readiness & config ───────────────────────────────────
    def is_ready(self):
        return bool(self.all_sheets) and any(r.is_ready() for r in self._sheet_rows)

    def get_configs(self) -> list[dict]:
        """Returns list of {sheet_name, df, key, cols} for each ready sheet row."""
        return [r.get_config() for r in self._sheet_rows if r.is_ready()]

# ══════════════════════════════════════════════════════════════
#  RESULT TAB — one treeview tab per comparison pair
# ══════════════════════════════════════════════════════════════
class ResultTab(ctk.CTkFrame):
    def __init__(self, master, df, tab_label):
        super().__init__(master, fg_color=BG)
        self._df        = df
        self._tab_label = tab_label
        self._build()

    def _build(self):
        # stats + filter row
        top = ctk.CTkFrame(self, fg_color=BG)
        top.pack(fill="x", pady=(4,4))

        self._stats_var = ctk.StringVar(value="—")
        ctk.CTkLabel(top, textvariable=self._stats_var, font=(F,8),
                     text_color=TEXT_MED, fg_color=BG).pack(side="left")

        ctk.CTkLabel(top,text="⌕",font=(F,12),text_color=TEXT_MED,
                     fg_color=BG).pack(side="left",padx=(12,0))
        self._fq = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=self._fq, width=170, height=24,
                     fg_color=SURFACE, border_color=BORDER,
                     text_color=TEXT, font=(F,8),
                     placeholder_text="filtrar..."
                     ).pack(side="left", padx=(4,0))
        self._fq.trace("w", lambda*_: self._apply())

        self._show = ctk.StringVar(value="all")
        for val,lbl,clr in [("all","TODOS",TEXT),("match","✔ MATCHES",GREEN),("nomatch","✘ AUSENTES",RED)]:
            ctk.CTkRadioButton(top, text=lbl, variable=self._show, value=val,
                                font=(F,8), text_color=clr,
                                fg_color=CYAN_DIM, hover_color=CYAN,
                                command=self._apply).pack(side="left", padx=(8,0))

        # treeview
        tw = ctk.CTkFrame(self, fg_color=BORDER, corner_radius=0)
        tw.pack(fill="both", expand=True)
        inner = tk.Frame(tw, bg=BG2)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        self._tree = ttk.Treeview(inner, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(inner, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(inner, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",fill="y"); hsb.pack(side="bottom",fill="x")
        self._tree.pack(fill="both", expand=True)

        self._tree.tag_configure("match",   background="#071a0d", foreground=GREEN)
        self._tree.tag_configure("partial", background="#141000", foreground=AMBER)
        self._tree.tag_configure("nomatch", background="#160507", foreground=RED)
        self._tree.tag_configure("even",    background="#07101a")
        self._tree.bind("<Double-1>", self._row_detail)

        self._apply()

    @staticmethod
    def _hidden(df): return {c for c in df.columns if c.startswith("__")}

    def _apply(self):
        if self._df is None: return
        df = self._df.copy()
        show = self._show.get()
        if show=="match"   and "__match_any__" in df.columns: df=df[df["__match_any__"]]
        elif show=="nomatch" and "__match_any__" in df.columns: df=df[~df["__match_any__"]]
        q=self._fq.get().strip().lower()
        if q:
            hide=self._hidden(df); vis=[c for c in df.columns if c not in hide]
            mask=df[vis].apply(lambda row:row.astype(str).str.lower().str.contains(q).any(),axis=1)
            df=df[mask]
        self._render(df)

    def _render(self, df):
        self._tree.delete(*self._tree.get_children())
        if df is None or df.empty: self._stats_var.set("Sem resultados"); return
        hide=self._hidden(df); vcols=[c for c in df.columns if c not in hide]
        mcols=[c for c in df.columns if c.startswith("__match_ref")]
        self._tree["columns"]=vcols
        for c in vcols:
            self._tree.heading(c,text=c,anchor="w")
            mx=max(len(str(c)), df[c].astype(str).str.len().max() if len(df) else len(c))
            self._tree.column(c,width=max(70,min(230,int(mx*7+16))),minwidth=50)
        for i,(_,row) in enumerate(df.iterrows()):
            vals=[str(row[c]) if pd.notna(row.get(c)) else "" for c in vcols]
            if mcols:
                n=sum(bool(row.get(mc,False)) for mc in mcols)
                tag="match" if n==len(mcols) else ("partial" if n else "nomatch")
            elif "__match_any__" in row.index:
                tag="match" if row["__match_any__"] else "nomatch"
            else: tag="even" if i%2 else ""
            self._tree.insert("","end",values=vals,tags=(tag,))
        if "__match_any__" in self._df.columns:
            n=len(self._df); nm=int(self._df["__match_any__"].sum())
            pct=nm/n*100 if n else 0
            self._stats_var.set(f"{n:,} total  ·  {nm:,} matches ({pct:.1f}%)  ·  {n-nm:,} ausentes")
        else: self._stats_var.set(f"{len(df):,} linhas")

    def _row_detail(self, _):
        sel=self._tree.selection()
        if not sel: return
        vals=self._tree.item(sel[0],"values"); cols=self._tree["columns"]
        win=ctk.CTkToplevel(self); win.title("Row Detail")
        win.configure(fg_color=BG); win.geometry("460x480"); win.grab_set()
        ctk.CTkLabel(win,text="◈  ROW DETAIL",font=(F,11,"bold"),
                     text_color=CYAN,fg_color=BG).pack(padx=16,pady=(12,6))
        sf=ctk.CTkScrollableFrame(win,fg_color=CARD,border_color=BORDER,
                                   border_width=1,width=420,height=380)
        sf.pack(padx=16,pady=4)
        for c,v in zip(cols,vals):
            r=ctk.CTkFrame(sf,fg_color=CARD); r.pack(fill="x",padx=4,pady=2)
            ctk.CTkLabel(r,text=f"{c}:",width=160,font=(F,8,"bold"),
                         text_color=TEXT_MED,fg_color=CARD,anchor="w").pack(side="left")
            ctk.CTkLabel(r,text=str(v),font=(F,9),
                         text_color=WHITE,fg_color=CARD,anchor="w").pack(side="left")
        ctk.CTkButton(win,text="FECHAR",width=100,height=28,
                       fg_color=SURFACE,hover_color=BORDER_HI,
                       text_color=CYAN,font=(F,8),
                       command=win.destroy).pack(pady=8)

    def get_export_df(self, mode="all"):
        if self._df is None: return pd.DataFrame()
        df=self._df.copy()
        hide=self._hidden(df)
        if mode=="match"   and "__match_any__" in df.columns: df=df[df["__match_any__"]]
        elif mode=="nomatch" and "__match_any__" in df.columns: df=df[~df["__match_any__"]]
        return df.drop(columns=[c for c in hide if c in df.columns])

# ══════════════════════════════════════════════════════════════
#  RESULTS PANEL — tabbed, one tab per comparison pair
# ══════════════════════════════════════════════════════════════
class ResultsPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self._tabs: dict[str, ResultTab] = {}  # tab_label -> ResultTab
        self._results: dict[str, pd.DataFrame] = {}
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color=BG)
        hdr.pack(fill="x", pady=(0,4))
        ctk.CTkLabel(hdr, text="◈  RESULTS", font=(F,10,"bold"),
                     text_color=CYAN, fg_color=BG).pack(side="left")
        self._total_var = ctk.StringVar(value="—")
        ctk.CTkLabel(hdr, textvariable=self._total_var, font=(F,8),
                     text_color=TEXT_MED, fg_color=BG).pack(side="left", padx=12)

        # Export buttons
        for lbl,fg,mode,bw in [("⬇ EXPORTAR TUDO (multi-sheet)",WHITE,"all",230),
                                ("⬇ SÓ MATCHES",GREEN,"match",120),
                                ("⬇ SÓ AUSENTES",RED,"nomatch",120)]:
            ctk.CTkButton(hdr, text=lbl, width=bw, height=26,
                           fg_color=SURFACE, hover_color=BORDER_HI,
                           text_color=fg, font=(F,8,"bold"),
                           border_color=BORDER, border_width=1,
                           command=lambda m=mode: self._export(m)
                           ).pack(side="right", padx=(0,5))

        # Tab view
        self._tabview = ctk.CTkTabview(self, fg_color=CARD,
                                        segmented_button_fg_color=BG3,
                                        segmented_button_selected_color=CYAN_DIM,
                                        segmented_button_selected_hover_color=CYAN,
                                        segmented_button_unselected_color=BG3,
                                        segmented_button_unselected_hover_color=BORDER_HI,
                                        text_color=TEXT,
                                        text_color_disabled=TEXT_DIM,
                                        border_color=BORDER, border_width=1)
        self._tabview.pack(fill="both", expand=True)

        # Placeholder tab — CTkTabview uses grid internally so we must
        # add a proper tab instead of packing a widget directly into it
        self._PLACEHOLDER = "— aguardando —"
        self._tabview.add(self._PLACEHOLDER)
        ctk.CTkLabel(self._tabview.tab(self._PLACEHOLDER),
                     text="Execute uma comparação para ver os resultados aqui",
                     font=(F,9), text_color=TEXT_DIM, fg_color=CARD
                     ).pack(expand=True, fill="both", pady=40)

    def display_all(self, results: dict[str, pd.DataFrame]):
        """results = {tab_label: df}"""
        self._results = results

        # Remove placeholder if present
        if self._PLACEHOLDER in [self._tabview.tab(t) and t
                                  for t in self._tabview._tab_dict]:
            try: self._tabview.delete(self._PLACEHOLDER)
            except: pass

        # Clear existing result tabs
        for name in list(self._tabs.keys()):
            try: self._tabview.delete(name)
            except: pass
        self._tabs.clear()

        # Also delete placeholder cleanly
        try: self._tabview.delete(self._PLACEHOLDER)
        except: pass

        total_rows = sum(len(df) for df in results.values())
        total_matches = sum(
            int(df["__match_any__"].sum()) if "__match_any__" in df.columns else 0
            for df in results.values())
        pct = total_matches/total_rows*100 if total_rows else 0
        self._total_var.set(
            f"{len(results)} comparações  ·  {total_rows:,} rows  ·  "
            f"{total_matches:,} matches ({pct:.1f}%)")

        for label, df in results.items():
            # Truncate tab name to fit
            tab_name = label[:28] + "…" if len(label) > 28 else label
            # Ensure unique
            tab_name_orig = tab_name
            suffix = 1
            while tab_name in self._tabs:
                tab_name = f"{tab_name_orig[:25]}_{suffix}"; suffix+=1

            self._tabview.add(tab_name)
            tab_frame = self._tabview.tab(tab_name)

            rt = ResultTab(tab_frame, df, label)
            rt.pack(fill="both", expand=True)
            self._tabs[tab_name] = rt

        # Select first tab
        if self._tabs:
            first = next(iter(self._tabs))
            try: self._tabview.set(first)
            except: pass

    def _export(self, mode):
        if not self._results:
            messagebox.showwarning("Nada exportar","Execute uma comparação primeiro.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel","*.xlsx")],
            initialfile=f"xlookup_export_{mode}.xlsx")
        if not path: return
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for tab_name, rt in self._tabs.items():
                    df = rt.get_export_df(mode)
                    if df.empty: continue
                    # Excel sheet names: max 31 chars, no special chars
                    safe_name = tab_name.replace("/","_").replace("\\","_")[:31]
                    df.to_excel(writer, sheet_name=safe_name, index=False)
            messagebox.showinfo("✔ Exportado!",
                                f"Excel multi-sheet salvo em:\n{path}\n\n"
                                f"{len(self._tabs)} sheets exportadas.")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

# ══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("XLOOKUP ENGINE  v3.0")
        self.configure(fg_color=BG)

        sw=self.winfo_screenwidth(); sh=self.winfo_screenheight()
        w=min(1300,sw-40); h=min(900,sh-60)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(960,620)

        _tree_style()
        self._q          = queue.Queue()
        self.ref_panels: list[FilePanel] = []
        self._ref_idx    = 0
        self._comparing  = False

        self._build()
        self._poll()
        self.bind("<Control-Return>",   lambda _: self._run())
        self.bind("<Control-KP_Enter>", lambda _: self._run())

    # ── UI BUILD ─────────────────────────────────────────────
    def _build(self):
        self._build_titlebar()
        ctk.CTkFrame(self, height=1, fg_color=CYAN, corner_radius=0).pack(fill="x")
        self._build_body()
        self._build_statusbar()
        self._add_ref()

    def _build_titlebar(self):
        tb=ctk.CTkFrame(self,height=44,fg_color=BG3,corner_radius=0)
        tb.pack(fill="x"); tb.pack_propagate(False)
        GlowTitle(tb,text="◈  XLOOKUP  ENGINE").pack(side="left",padx=12,pady=6)
        ctk.CTkLabel(tb,text="v3.0  ·  multi-sheet  ·  multi-ref  ·  async I/O  ·  Ctrl+Enter to run",
                     font=(F,7),text_color=TEXT_DIM,fg_color=BG3).pack(side="left",padx=(0,20))
        self._hdr_var=ctk.StringVar(value="● aguardando...")
        self._hdr_lbl=ctk.CTkLabel(tb,textvariable=self._hdr_var,
                                    font=(F,8),text_color=TEXT_DIM,fg_color=BG3)
        self._hdr_lbl.pack(side="right",padx=14)

    def _build_body(self):
        outer=ctk.CTkFrame(self,fg_color=BG,corner_radius=0)
        outer.pack(fill="both",expand=True,padx=10,pady=6)

        # ── FILES ROW
        files_row=ctk.CTkFrame(outer,fg_color=BG)
        files_row.pack(fill="x",pady=(0,5))

        # BASE
        base_col=ctk.CTkFrame(files_row,fg_color=BG,width=380)
        base_col.pack(side="left",fill="y",padx=(0,8))
        base_col.pack_propagate(False)
        bh=ctk.CTkFrame(base_col,fg_color=BG); bh.pack(fill="x",pady=(0,3))
        ctk.CTkLabel(bh,text="[ BASE FILE ]",font=(F,8,"bold"),
                     text_color=CYAN,fg_color=BG).pack(side="left")
        ctk.CTkLabel(bh,text="arquivo de origem",font=(F,7),
                     text_color=TEXT_DIM,fg_color=BG).pack(side="left",padx=6)
        self.base_panel=FilePanel(base_col,label="BASE",color=CYAN,
                                   app_queue=self._q,on_ready=self._file_ready)
        self.base_panel.hide_x()
        self.base_panel.pack(fill="both",expand=True)

        # REFS
        refs_col=ctk.CTkFrame(files_row,fg_color=BG)
        refs_col.pack(side="left",fill="both",expand=True)
        rh=ctk.CTkFrame(refs_col,fg_color=BG); rh.pack(fill="x",pady=(0,3))
        ctk.CTkLabel(rh,text="[ REFERENCE FILES ]",font=(F,8,"bold"),
                     text_color=MAGENTA,fg_color=BG).pack(side="left")
        ctk.CTkLabel(rh,text="N arquivos · N sheets cada",font=(F,7),
                     text_color=TEXT_DIM,fg_color=BG).pack(side="left",padx=6)
        ctk.CTkButton(rh,text="  +  ADICIONAR  ",width=130,height=24,
                       fg_color=MAG_DIM,hover_color=MAGENTA,
                       text_color=WHITE,font=(F,8,"bold"),
                       border_color=MAGENTA,border_width=1,
                       command=self._add_ref).pack(side="right")
        self._refs_scroll=ctk.CTkScrollableFrame(
            refs_col,fg_color=BG2,border_color=BORDER,border_width=1,height=185)
        self._refs_scroll.pack(fill="both",expand=True)
        self._ref_ph=ctk.CTkLabel(self._refs_scroll,
            text="Clique em  +  ADICIONAR  para incluir arquivos de referência",
            font=(F,9),text_color=TEXT_DIM,fg_color=BG2)
        self._ref_ph.pack(pady=28)

        # ── OPTIONS + RUN (always visible)
        opts=ctk.CTkFrame(outer,fg_color=CARD,border_color=BORDER,border_width=1)
        opts.pack(fill="x",pady=(0,5))
        row=ctk.CTkFrame(opts,fg_color=CARD); row.pack(fill="x",padx=10,pady=7)

        ctk.CTkLabel(row,text="JOIN:",font=(F,8),
                     text_color=TEXT_MED,fg_color=CARD).pack(side="left",padx=(0,4))
        self._join=ctk.StringVar(value="left")
        for val,lbl in [("left","LEFT"),("inner","INNER"),("outer","OUTER"),("right","RIGHT")]:
            ctk.CTkRadioButton(row,text=lbl,variable=self._join,value=val,
                                font=(F,8),text_color=TEXT,
                                fg_color=CYAN_DIM,hover_color=CYAN).pack(side="left",padx=4)

        ctk.CTkFrame(row,width=1,fg_color=BORDER).pack(side="left",fill="y",padx=8)
        self._case=ctk.BooleanVar(value=False)
        self._strip=ctk.BooleanVar(value=True)
        for var,lbl in [(self._case,"Case-insensitive"),(self._strip,"Strip espaços")]:
            ctk.CTkCheckBox(row,text=lbl,variable=var,font=(F,8),
                             text_color=TEXT,fg_color=CYAN_DIM,
                             hover_color=CYAN,checkmark_color=WHITE).pack(side="left",padx=6)

        ctk.CTkFrame(row,width=1,fg_color=BORDER).pack(side="left",fill="y",padx=8)

        self._run_btn=ctk.CTkButton(
            row,text="▶  EXECUTAR",width=155,height=34,
            fg_color=CYAN_DIM,hover_color=CYAN,
            text_color=WHITE,font=(F,10,"bold"),
            border_color=CYAN,border_width=1,
            command=self._run)
        self._run_btn.pack(side="left",padx=(0,8))

        self._prog=ctk.CTkProgressBar(row,width=120,height=7,
                                       fg_color=BG3,progress_color=CYAN,
                                       mode="indeterminate")
        self._run_lbl_var=ctk.StringVar(value="Ctrl+Enter para executar")
        self._run_lbl=ctk.CTkLabel(row,textvariable=self._run_lbl_var,
                                    font=(F,8),text_color=TEXT_DIM,fg_color=CARD)
        self._run_lbl.pack(side="left")

        # ── RESULTS (tabbed)
        self._results=ResultsPanel(outer)
        self._results.pack(fill="both",expand=True)

    def _build_statusbar(self):
        ctk.CTkFrame(self,height=1,fg_color=BORDER,corner_radius=0).pack(fill="x")
        sb=ctk.CTkFrame(self,height=20,fg_color=BG3,corner_radius=0)
        sb.pack(fill="x"); sb.pack_propagate(False)
        ctk.CTkLabel(sb,
            text="  ◈ XLOOKUP ENGINE v3.0  ·  multi-sheet Excel export  ·  double-click → detail  ·  Ctrl+Enter",
            font=(F,7),text_color=TEXT_DIM,fg_color=BG3).pack(side="left")

    # ── REF MANAGEMENT ───────────────────────────────────────
    def _add_ref(self):
        if self._ref_ph.winfo_ismapped(): self._ref_ph.pack_forget()
        self._ref_idx+=1
        i=self._ref_idx; color=REF_COLORS[(i-1)%len(REF_COLORS)]; label=f"REF-{i:02d}"
        wrapper=ctk.CTkFrame(self._refs_scroll,fg_color=BG2)
        wrapper.pack(fill="x",padx=4,pady=3)
        panel=FilePanel(wrapper,label=label,color=color,
                         app_queue=self._q,on_ready=self._file_ready)
        panel.pack(fill="x")
        self.ref_panels.append(panel)

        def make_remover(p=panel,w=wrapper):
            def _remove():
                if p in self.ref_panels: self.ref_panels.remove(p)
                w.destroy()
                if not self.ref_panels: self._ref_ph.pack(pady=28)
                self._file_ready()
            return _remove
        panel._remove_cb=make_remover()
        self._refs_scroll.after(50,
            lambda: self._refs_scroll._parent_canvas.yview_moveto(1.0))

    # ── QUEUE POLL ───────────────────────────────────────────
    def _poll(self):
        try:
            while True:
                msg=self._q.get_nowait(); kind=msg[0]
                if kind=="loaded":
                    _,pid,path,sheets,err=msg
                    for p in [self.base_panel]+self.ref_panels:
                        if id(p)==pid: p.receive_load(path,sheets,err); break
                elif kind=="compare_done": self._on_done(msg[1])
                elif kind=="compare_err":  self._on_err(msg[1])
        except queue.Empty: pass
        self.after(38,self._poll)

    def _file_ready(self):
        ready=sum(1 for p in [self.base_panel]+self.ref_panels if p.is_ready())
        total=1+len(self.ref_panels)
        color=GREEN if ready==total else AMBER
        self._hdr_var.set(f"● {ready}/{total} prontos")
        self._hdr_lbl.configure(text_color=color)

    # ── COMPARE ──────────────────────────────────────────────
    def _run(self):
        if self._comparing: return
        if not self.base_panel.is_ready():
            messagebox.showwarning("Base file","Carregue o arquivo BASE primeiro."); return
        ready_refs=[p for p in self.ref_panels if p.is_ready()]
        if not ready_refs:
            messagebox.showwarning("Referências","Carregue ao menos um arquivo de referência."); return
        self._comparing=True
        self._run_btn.configure(state="disabled")
        self._prog.pack(side="left",padx=(8,0)); self._prog.start()
        self._run_lbl_var.set("  comparando...")
        self._run_lbl.configure(text_color=AMBER)
        threading.Thread(target=self._compare,args=(ready_refs,),daemon=True).start()

    def _compare(self, ref_panels):
        try:
            base_configs = self.base_panel.get_configs()   # list of sheet configs
            join         = self._join.get()
            case         = self._case.get()
            strip        = self._strip.get()
            results      = {}   # tab_label -> df

            # Collect all ref sheet configs per ref panel
            all_ref_configs = []
            for rp in ref_panels:
                for rc in rp.get_configs():
                    rc["panel_label"] = rp._label
                    all_ref_configs.append(rc)

            # One comparison per (base_sheet × ref_sheet)
            for bc in base_configs:
                bdf  = bc["df"][bc["cols"]].copy()
                bkey = bc["key"]
                bname = bc["sheet_name"]

                if strip: bdf[bkey] = bdf[bkey].astype(str).str.strip()
                if case:  bdf["__jk__"] = bdf[bkey].str.lower()

                for i, rc in enumerate(all_ref_configs, 1):
                    rdf    = rc["df"].copy()
                    rkey   = rc["key"]
                    rlabel = f"{rc['panel_label']}:{rc['sheet_name']}"
                    rcols  = list(dict.fromkeys([rkey] + rc["cols"]))
                    rsub   = rdf[rcols].copy()

                    if strip: rsub[rkey] = rsub[rkey].astype(str).str.strip()

                    rename = {c: f"{c}[{rlabel}]"
                              for c in rsub.columns
                              if c != rkey and c in bdf.columns}
                    if rename: rsub = rsub.rename(columns=rename)

                    if case:
                        rsub["__jk__"] = rsub[rkey].str.lower()
                        lon, ron = "__jk__", "__jk__"
                    else:
                        lon, ron = bkey, rkey

                    merged = bdf.merge(rsub, how=join,
                                       left_on=lon, right_on=ron,
                                       suffixes=("", f"_dup{i}"))

                    merged["__match_any__"] = merged[rkey].notna()
                    drop = ["__jk__", f"__jk___dup{i}"]
                    if ron != lon: drop.append(rkey)
                    merged = merged.drop(columns=[c for c in drop if c in merged.columns])

                    tab_label = f"{bname}  ↔  {rlabel}"
                    results[tab_label] = merged

            self._q.put(("compare_done", results))
        except Exception:
            import traceback
            self._q.put(("compare_err", traceback.format_exc()))

    def _on_done(self, results):
        self._comparing=False; self._prog.stop(); self._prog.pack_forget()
        self._run_btn.configure(state="normal")
        total = sum(len(df) for df in results.values())
        matches = sum(int(df["__match_any__"].sum()) if "__match_any__" in df.columns else 0
                      for df in results.values())
        pct = matches/total*100 if total else 0
        self._run_lbl_var.set(
            f"  ✔  {len(results)} tabs  ·  {total:,} rows  ·  {matches:,} matches ({pct:.1f}%)")
        self._run_lbl.configure(text_color=GREEN)
        self._hdr_var.set(f"● concluído  ·  {len(results)} comparações")
        self._hdr_lbl.configure(text_color=GREEN)
        self._results.display_all(results)

    def _on_err(self, err):
        self._comparing=False; self._prog.stop(); self._prog.pack_forget()
        self._run_btn.configure(state="normal")
        self._run_lbl_var.set("  ✘  erro na comparação")
        self._run_lbl.configure(text_color=RED)
        messagebox.showerror("Erro na comparação", err)

# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()