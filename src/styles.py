"""
TTK Treeview theming para o XLOOKUP ENGINE.
"""

from tkinter import ttk
from src.constants import BG, BG2, BG3, BORDER, CYAN, TEXT, WHITE, F


def apply_tree_style() -> None:
    """Aplica o tema dark ao ttk.Treeview e scrollbars."""
    s = ttk.Style()
    try:
        s.theme_use("clam")
    except Exception:
        pass

    s.configure(
        "Treeview",
        background=BG2,
        foreground=TEXT,
        fieldbackground=BG2,
        rowheight=22,
        font=(F, 9),
    )
    s.configure(
        "Treeview.Heading",
        background=BG3,
        foreground=CYAN,
        font=(F, 9, "bold"),
        relief="flat",
    )
    s.map(
        "Treeview",
        background=[("selected", BORDER)],
        foreground=[("selected", WHITE)],
    )
    s.configure(
        "TScrollbar",
        background=BG3,
        troughcolor=BG,
        arrowcolor=CYAN,
        borderwidth=0,
        relief="flat",
    )
