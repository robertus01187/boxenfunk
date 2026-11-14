"""Grundgerüst für ein Overlay-Fenster: durchsichtig, rahmenlos, immer im Vordergrund.

Im Rennen klickt man durch die Fenster hindurch (``locked``). Im Verschiebe-Modus bekommen
sie einen gestrichelten Rahmen und lassen sich mit der Maus ziehen.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import QWidget

from boxenfunk.core.tracker import SessionTracker
from boxenfunk.model.race_state import RaceState

FONT_DIR = Path(__file__).with_name("fonts")
_family: str | None = None


def font_family() -> str:
    """Exo 2 (Schrift aus dem Design, OFL-Lizenz), sonst Segoe UI."""
    global _family
    if _family is None:
        fams: list[str] = []
        for f in ("Exo2.ttf", "Exo2-Italic.ttf"):
            fid = QFontDatabase.addApplicationFont(str(FONT_DIR / f))
            if fid >= 0:
                fams += QFontDatabase.applicationFontFamilies(fid)
        _family = fams[0] if fams else "Segoe UI"
    return _family


def ov_font(px: float, weight: int = 600, italic: bool = False) -> QFont:
    f = QFont(font_family())
    f.setPixelSize(max(6, round(px)))
    f.setWeight(QFont.Weight(weight))
    f.setItalic(italic)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


# Farben aus dem Design (docs/design, Standings-Muster)
WHITE = QColor("#ffffff")
DIM = QColor("#9aa3b0")
GAIN = QColor("#52e05a")
LOSS = QColor("#ff7a62")
PB = QColor("#1fbf4a")
OB = QColor("#b23cff")
ME = QColor("#1e8b96")
ME_BAR = QColor("#38c6d4")
YELLOW = QColor("#f5c518")
ORANGE = QColor("#ff9f1c")
RED = QColor("#ff4040")
BLUE = QColor("#5aa9ff")
VE_BLUE = QColor("#3d8bfd")
HDR_BG = QColor(26, 30, 38, 225)
ROW_A = QColor(22, 30, 42, 215)
ROW_B = QColor(30, 38, 52, 215)
ME_BG = QColor(26, 110, 120, 235)

TYRE_COLORS = {
    "soft": QColor("#ff4040"),
    "medium": QColor("#f5c518"),
    "hard": QColor("#ffffff"),
    "wet": QColor("#3d8bfd"),
    "inter": QColor("#3ddc84"),
}


def fmt_lap(t: float | None) -> str:
    if t is None or t <= 0:
        return "-"
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:06.3f}" if m else f"{s:.3f}"


def fmt_lap_short(t: float | None) -> str:
    if t is None or t <= 0:
        return "-"
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:04.1f}" if m else f"{s:.1f}"


def fmt_clock(t: float | None) -> str:
    if t is None:
        return "-"
    t = max(0, int(t))
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def fmt_gap(t: float | None) -> str:
    if t is None:
        return ""
    if abs(t) >= 100:
        return f"{t:.0f}"
    return f"{t:.1f}"


class Overlay(QWidget):
    """Basisklasse. Unterklassen implementieren ``paint_overlay`` und ``preferred_size``."""

    moved = Signal()
    key = "overlay"
    title = "Overlay"

    def __init__(self, scale: float = 1.0) -> None:
        super().__init__(None)
        self.scale = scale
        self.state: RaceState | None = None
        self.tracker: SessionTracker | None = None
        self._locked = True
        self._drag_from: QPoint | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle(f"Boxenfunk – {self.title}")
        self._apply_flags()

    # -- Fenster-Verhalten --

    def _apply_flags(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        if self._locked:
            flags |= (
                Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowDoesNotAcceptFocus
            )
        visible = self.isVisible()
        self.setWindowFlags(flags)
        if visible:
            self.show()

    def set_locked(self, locked: bool) -> None:
        if locked != self._locked:
            self._locked = locked
            self._apply_flags()
            self.update()

    @property
    def locked(self) -> bool:
        return self._locked

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        self.relayout()

    def relayout(self) -> None:
        w, h = self.preferred_size()
        if (w, h) != (self.width(), self.height()):
            self.setFixedSize(max(10, int(w)), max(10, int(h)))

    def mousePressEvent(self, e) -> None:  # noqa: N802 (Qt-Name)
        if not self._locked and e.button() == Qt.MouseButton.LeftButton:
            self._drag_from = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._drag_from is not None:
            self.move(e.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if self._drag_from is not None:
            self._drag_from = None
            self.moved.emit()

    # -- Daten und Zeichnen --

    def set_data(self, state: RaceState | None, tracker: SessionTracker | None) -> None:
        self.state = state
        self.tracker = tracker
        self.on_data()
        self.relayout()
        self.update()

    def on_data(self) -> None:
        """Für Widgets, die Verläufe sammeln (z. B. Inputs)."""

    def preferred_size(self) -> tuple[float, float]:
        return 200 * self.scale, 100 * self.scale

    def paintEvent(self, _e) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self.state is not None and self.tracker is not None:
            self.paint_overlay(p)
        else:
            self.paint_placeholder(p)
        if not self._locked:
            p.setPen(QPen(YELLOW, 2, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(self.rect()).adjusted(1, 1, -1, -1))
            p.setFont(ov_font(11 * self.scale))
            p.setPen(YELLOW)
            p.drawText(
                QRectF(self.rect()).adjusted(6, 2, -6, -2),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                self.title,
            )
        p.end()

    def paint_placeholder(self, p: QPainter) -> None:
        if self._locked:
            return
        p.fillRect(self.rect(), HDR_BG)
        p.setFont(ov_font(14 * self.scale))
        p.setPen(DIM)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.title}\n(wartet auf Daten)")

    def paint_overlay(self, p: QPainter) -> None:
        raise NotImplementedError


def text(
    p: QPainter,
    x: float,
    y: float,
    w: float,
    h: float,
    s: str,
    color: QColor,
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
) -> None:
    p.setPen(color)
    p.drawText(QRectF(x, y, w, h), align | Qt.AlignmentFlag.AlignVCenter, s)


RIGHT = Qt.AlignmentFlag.AlignRight
CENTER = Qt.AlignmentFlag.AlignHCenter
LEFT = Qt.AlignmentFlag.AlignLeft
