"""
GlowTitle — label animado com efeito glow ciano (sem Canvas).
"""

import math
import customtkinter as ctk
from src.constants import CYAN, BG3, F


class GlowTitle(ctk.CTkLabel):
    """Título que pulsa em tons de ciano usando apenas CTkLabel."""

    _PALETTE: list[str] = [
        f"#00{int(229 * (0.55 + 0.45 * math.sin(i * math.pi * 2 / 16))):02x}"
        f"{int(255 * (0.55 + 0.45 * math.sin(i * math.pi * 2 / 16))):02x}"
        for i in range(16)
    ]

    def __init__(self, master, text: str, **kw):
        super().__init__(
            master,
            text=text,
            font=(F, 14, "bold"),
            text_color=CYAN,
            fg_color=BG3,
            anchor="w",
            **kw,
        )
        self._fi: int = 0
        self._active: bool = True
        self._tick()

    def destroy(self) -> None:
        self._active = False
        super().destroy()

    def _tick(self) -> None:
        if not self._active:
            return
        try:
            self.configure(text_color=self._PALETTE[self._fi % len(self._PALETTE)])
        except Exception:
            pass
        self._fi += 1
        self.after(80, self._tick)
