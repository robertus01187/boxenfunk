"""Grundgerüst für ein Overlay-Fenster: durchsichtig, rahmenlos, immer im Vordergrund.

Im Rennen klickt man durch die Fenster hindurch (``locked``). Im Verschiebe-Modus bekommen
sie einen gestrichelten Rahmen und lassen sich mit der Maus ziehen.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QPolygonF
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
    fast = False  # True = bekommt die schnellen Eingabe-Daten (60-mal pro Sekunde)
    title = "Overlay"

    def __init__(self, scale: float = 1.0) -> None:
        super().__init__(None)
        self.scale = scale
        self.state: RaceState | None = None
        self.tracker: SessionTracker | None = None
        self._locked = True
        self._drag_from: QPoint | None = None
        self._resize_from: tuple[QPoint, float, int] | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
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

    # Strecken: Breite/Höhe als Faktor zur natürlichen Größe. Widgets zeichnen in die echte
    # Fenstergröße und blenden Teile aus, wenn der Platz nicht reicht.
    can_stretch_w = True
    can_stretch_h = True
    stretch_w = 1.0
    stretch_h = 1.0

    def min_size(self) -> tuple[float, float]:
        """Kleinste sinnvolle Größe (Pixel). Kleiner lässt sich das Widget nicht ziehen."""
        w, h = self.preferred_size()
        return w * 0.6, h * 0.6

    def set_stretch(self, sw: float, sh: float) -> None:
        self.stretch_w = sw if self.can_stretch_w else 1.0
        self.stretch_h = sh if self.can_stretch_h else 1.0
        self.relayout()

    def relayout(self) -> None:
        w, h = self.preferred_size()
        mw, mh = self.min_size()
        w = max(mw, w * self.stretch_w)
        h = max(mh, h * self.stretch_h)
        if (int(w), int(h)) != (self.width(), self.height()):
            self.setFixedSize(max(10, int(w)), max(10, int(h)))

    # Ecke unten rechts: alles gleichmäßig größer/kleiner. Ränder: nur breiter/höher.
    HANDLE = 18
    EDGE = 8
    MIN_SCALE, MAX_SCALE = 0.4, 3.0

    def _in_handle(self, pos) -> bool:
        return pos.x() >= self.width() - self.HANDLE and pos.y() >= self.height() - self.HANDLE

    def _edge_at(self, pos) -> str:
        """Welcher Rand unter der Maus liegt: Buchstaben aus "lrtb" (leer = keiner)."""
        e = ""
        if self.can_stretch_w:
            if pos.x() <= self.EDGE:
                e += "l"
            elif pos.x() >= self.width() - self.EDGE:
                e += "r"
        if self.can_stretch_h:
            if pos.y() <= self.EDGE:
                e += "t"
            elif pos.y() >= self.height() - self.EDGE:
                e += "b"
        return e

    def mousePressEvent(self, e) -> None:  # noqa: N802 (Qt-Name)
        if self._locked or e.button() != Qt.MouseButton.LeftButton:
            return
        g = e.globalPosition().toPoint()
        pos = e.position().toPoint()
        if self._in_handle(pos):
            self._resize_from = (g, self.scale, max(1, self.width()))
        elif edge := self._edge_at(pos):
            self._stretch_from = (g, edge, self.geometry(), *self.preferred_size())
        else:
            self._drag_from = g - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        g = e.globalPosition().toPoint()
        if self._resize_from is not None:
            start, s0, w0 = self._resize_from
            new_w = max(20, w0 + (g.x() - start.x()))
            scale = min(self.MAX_SCALE, max(self.MIN_SCALE, s0 * new_w / w0))
            self.set_scale(round(scale, 3))
            self.update()
        elif getattr(self, "_stretch_from", None) is not None:
            start, edge, geo, nw, nh = self._stretch_from
            dx, dy = g.x() - start.x(), g.y() - start.y()
            mw, mh = self.min_size()
            x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
            if "r" in edge:
                w = max(mw, geo.width() + dx)
            if "l" in edge:
                w = max(mw, geo.width() - dx)
                x = geo.x() + geo.width() - w
            if "b" in edge:
                h = max(mh, geo.height() + dy)
            if "t" in edge:
                h = max(mh, geo.height() - dy)
                y = geo.y() + geo.height() - h
            self.set_stretch(w / nw if nw else 1.0, h / nh if nh else 1.0)
            self.move(int(x), int(y))
            self.update()
        elif self._drag_from is not None:
            self.move(g - self._drag_from)
        elif not self._locked:
            pos = e.position().toPoint()
            edge = self._edge_at(pos)
            if self._in_handle(pos):
                cur = Qt.CursorShape.SizeFDiagCursor
            elif edge in ("l", "r"):
                cur = Qt.CursorShape.SizeHorCursor
            elif edge in ("t", "b"):
                cur = Qt.CursorShape.SizeVerCursor
            elif edge in ("lt", "rb"):
                cur = Qt.CursorShape.SizeFDiagCursor
            elif edge:
                cur = Qt.CursorShape.SizeBDiagCursor
            else:
                cur = Qt.CursorShape.SizeAllCursor
            self.setCursor(cur)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if (
            self._drag_from is not None
            or self._resize_from is not None
            or getattr(self, "_stretch_from", None) is not None
        ):
            self._drag_from = None
            self._resize_from = None
            self._stretch_from = None
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
            p.save()
            self.paint_overlay(p)
            p.restore()
        else:
            self.paint_placeholder(p)
        if not self._locked:
            p.setPen(QPen(YELLOW, 2, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(self.rect()).adjusted(1, 1, -1, -1))
            # Griff zum Vergrößern/Verkleinern
            w, h, k = self.width(), self.height(), self.HANDLE
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(YELLOW)
            p.drawPolygon(QPolygonF([QPointF(w, h - k), QPointF(w, h), QPointF(w - k, h)]))
            p.setFont(ov_font(11 * self.scale))
            p.setPen(YELLOW)
            p.drawText(
                QRectF(self.rect()).adjusted(6, 2, -6 - self.HANDLE, -2),
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
