"""
PulseDot — indicador de estado animado (sem Canvas).
"""

import customtkinter as ctk
from src.constants import TEXT_DIM, GREEN, RED, AMBER, CARD, F


class PulseDot(ctk.CTkLabel):
    """Label-dot que anima cor de acordo com o estado atual."""

    _COLORS: dict[str, list[str]] = {
        "idle":    [TEXT_DIM],
        "ready":   [GREEN],
        "error":   [RED],
        "loading": [AMBER, "#a87000", "#ffcc44", "#a87000"],
    }

    def __init__(self, master, bg_color: str = CARD, **kw):
        super().__init__(
            master,
            text="●",
            font=(F, 10),
            text_color=TEXT_DIM,
            fg_color=bg_color,
            width=14,
            **kw,
        )
        self._state: str = "idle"
        self._fi: int = 0
        self._active: bool = True
        self._tick()

    def set_state(self, s: str) -> None:
        self._state = s
        self._fi = 0

    def destroy(self) -> None:
        self._active = False
        super().destroy()

    def _tick(self) -> None:
        if not self._active:
            return
        frames = self._COLORS.get(self._state, [TEXT_DIM])
        try:
            self.configure(text_color=frames[self._fi % len(frames)])
        except Exception:
            pass
        self._fi += 1
        self.after(120, self._tick)
