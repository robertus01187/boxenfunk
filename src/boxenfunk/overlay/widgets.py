"""Die ersten fünf Overlays (Prototyp): Standings, Relative, Delta, Inputs, VE & Sprit.

Aussehen nach den Mustern aus dem Design-Thread (Schrift Exo 2, dunkle Zeilen, eigene Zeile
türkis). Einstellungsfenster je Widget kommen später (T3/T4); hier gelten feste Werte.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtSvg import QSvgRenderer

from boxenfunk.core.views import energy_view, standings_blocks
from boxenfunk.model.race_state import CarState, PitState, SessionKind
from boxenfunk.overlay.base import (
    CENTER,
    DIM,
    GAIN,
    HDR_BG,
    LOSS,
    ME_BAR,
    ME_BG,
    OB,
    ORANGE,
    PB,
    RED,
    RIGHT,
    ROW_A,
    ROW_B,
    TYRE_COLORS,
    VE_BLUE,
    WHITE,
    YELLOW,
    Overlay,
    fmt_clock,
    fmt_lap,
    fmt_lap_short,
    ov_font,
    text,
)

# --- Herstellerlogos ---------------------------------------------------------


class Logos:
    """Lädt Logos (``<marke>.svg`` oder ``.png``, weiß) aus einem Ordner, sonst Kürzel."""

    def __init__(self, folder: Path | None) -> None:
        self.folder = folder
        self._cache: dict[tuple[str, int], QPixmap | None] = {}

    def get(self, brand: str, size: int) -> QPixmap | None:
        key = (brand, size)
        if key in self._cache:
            return self._cache[key]
        pm = None
        if self.folder and brand:
            for ext in ("svg", "png"):
                f = self.folder / f"{brand}.{ext}"
                if f.exists():
                    pm = self._load(f, size)
                    break
        self._cache[key] = pm
        return pm

    @staticmethod
    def _load(f: Path, size: int) -> QPixmap | None:
        if f.suffix == ".svg":
            r = QSvgRenderer(str(f))
            if not r.isValid():
                return None
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            vb = r.viewBoxF()
            if vb.width() > 0 and vb.height() > 0:
                k = min(size / vb.width(), size / vb.height())
                w, h = vb.width() * k, vb.height() * k
                r.render(p, QRectF((size - w) / 2, (size - h) / 2, w, h))
            else:
                r.render(p)
            p.end()
            return pm
        pm = QPixmap(str(f))
        if pm.isNull():
            return None
        return pm.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )


def draw_logo(
    p: QPainter, logos: Logos, car: CarState, x: float, y: float, w: float, h: float
) -> None:
    size = int(min(w, h) * 0.8)
    pm = logos.get(car.brand, size)
    if pm is not None:
        p.drawPixmap(int(x + (w - pm.width()) / 2), int(y + (h - pm.height()) / 2), pm)
        return
    ab = (car.brand[:3] or "?").upper()
    p.save()
    p.setFont(ov_font(h * 0.36, 700))
    text(p, x, y, w, h, ab, DIM, CENTER)
    p.restore()


def tyre_dot(p: QPainter, compound: str, cx: float, cy: float, r: float) -> None:
    col = TYRE_COLORS.get(compound.lower()[:6].rstrip(), None)
    if col is None:
        for k, v in TYRE_COLORS.items():
            if compound.lower().startswith(k):
                col = v
                break
    p.setPen(QPen(col or DIM, max(1.5, r * 0.32)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(cx, cy), r, r)


def session_letter(kind: SessionKind) -> str:
    return {"training": "T", "quali": "Q", "warmup": "W", "rennen": "R"}.get(kind.value, "?")


# --- Standings ----------------------------------------------------------------


class StandingsOverlay(Overlay):
    key = "standings"
    title = "Standings"

    # Spalten: (Name, Breite in Schrift-Einheiten)
    COLS = (
        ("pos", 1.7),
        ("gain", 2.4),
        ("num", 2.6),
        ("name", 9.0),
        ("logo", 2.0),
        ("gap", 3.3),
        ("int", 3.3),
        ("last", 4.4),
        ("tyre", 1.6),
        ("ve", 4.0),
        ("pit", 3.7),
        ("stops", 1.4),
        ("t1", 2.6),
        ("t2", 2.6),
        ("t3", 2.6),
    )

    def __init__(self, scale: float = 1.0, logos: Logos | None = None) -> None:
        self.logos = logos or Logos(None)
        self._rows = 0
        super().__init__(scale)

    @property
    def fs(self) -> float:
        return 15 * self.scale

    @property
    def rh(self) -> float:
        return 26 * self.scale

    def _cols(self) -> list[tuple[str, float]]:
        show_ve = self.state is None or any(c.energy is not None for c in self.state.cars[:1])
        return [(n, w * self.fs) for n, w in self.COLS if n != "ve" or show_ve]

    def on_data(self) -> None:
        if self.state is None or self.tracker is None:
            self._blocks = []
            return
        self._blocks = standings_blocks(self.state, self.tracker)

    def preferred_size(self) -> tuple[float, float]:
        width = sum(w for _, w in self._cols()) + 8 * self.scale
        blocks = getattr(self, "_blocks", [])
        n = sum(len(r) for _, r in blocks)
        gaps = sum(1 for _, rows in blocks for r in rows if r.gap_before)
        height = (
            self.rh * 1.25
            + 6 * self.scale
            + n * self.rh
            + len(blocks) * 6 * self.scale
            + gaps * 6 * self.scale
        )
        return width, max(height, self.rh * 3)

    def paint_overlay(self, p: QPainter) -> None:
        st = self.state
        s = self.scale
        fs = self.fs
        rh = self.rh
        # Kopfzeile
        me = st.player_car()
        parts = [session_letter(st.session_kind)]
        if st.time_remaining is not None:
            parts.append(fmt_clock(st.time_remaining))
        if me is not None:
            parts.append(f"Rd {me.laps + 1}")
        if st.track_temp is not None:
            parts.append(f"Strecke {st.track_temp:.0f}°")
        hdr = "   ".join(parts)
        p.setFont(ov_font(fs * 1.1))
        hw = p.fontMetrics().horizontalAdvance(hdr) + 20 * s
        hh = rh * 1.25
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(HDR_BG)
        p.drawRoundedRect(QRectF(0, 0, hw, hh), 4 * s, 4 * s)
        text(p, 10 * s, 0, hw, hh, hdr, WHITE)

        y = hh + 6 * s
        cols = self._cols()
        width = sum(w for _, w in cols)
        for _cls, rows in self._blocks:
            block_h = len(rows) * rh + sum(6 * s for r in rows if r.gap_before)
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0, y, width, block_h), 4 * s, 4 * s)
            p.save()
            p.setClipPath(clip)
            for k, row in enumerate(rows):
                if row.gap_before:
                    p.fillRect(QRectF(0, y, width, 6 * s), QColor(15, 20, 28, 200))
                    y += 6 * s
                self._paint_row(p, row, y, k, cols, width)
                y += rh
            p.restore()
            y += 6 * s

    def _paint_row(self, p: QPainter, row, y: float, k: int, cols, width: float) -> None:
        s, fs, rh = self.scale, self.fs, self.rh
        c = row.car
        bg = ME_BG if c.is_player else (ROW_A if k % 2 == 0 else ROW_B)
        p.fillRect(QRectF(0, y, width, rh), bg)
        if c.is_player:
            p.fillRect(QRectF(0, y, 5 * s, rh), ME_BAR)
        x = 0.0
        pad = 4 * s
        for name, w in cols:
            if name == "pos":
                p.setFont(ov_font(fs))
                text(p, x, y, w, rh, str(c.class_position), WHITE, RIGHT)
            elif name == "gain" and row.gained:
                up = row.gained > 0
                col = GAIN if up else LOSS
                self._chevron(p, x + 0.55 * fs, y + rh / 2, 0.32 * fs, up, col)
                p.setFont(ov_font(fs))
                text(p, x, y, w - pad / 2, rh, str(abs(row.gained)), col, RIGHT)
            elif name == "num":
                p.setFont(ov_font(fs, 600, italic=True))
                text(p, x, y, w - pad, rh, c.number, WHITE, RIGHT)
            elif name == "name":
                p.setFont(ov_font(fs))
                p.save()
                p.setClipRect(QRectF(x, y, w, rh))
                text(p, x + pad / 2, y, w * 2, rh, c.driver, DIM if c.in_pits else WHITE)
                p.restore()
            elif name == "logo":
                draw_logo(p, self.logos, c, x, y, w, rh)
            elif name in ("gap", "int"):
                p.setFont(ov_font(fs))
                val = row.gap if name == "gap" else row.interval
                if not val and c.class_position == 1:
                    text(p, x, y, w - pad, rh, name.upper(), WHITE, RIGHT)
                else:
                    text(p, x, y, w - pad, rh, val, WHITE, RIGHT)
            elif name == "last":
                p.setFont(ov_font(fs))
                text(p, x, y, w - pad, rh, fmt_lap_short(c.last_lap), WHITE, RIGHT)
                if row.last_kind:
                    p.fillRect(
                        QRectF(x + pad, y + rh - 3 * s, w - 2 * pad, 2.5 * s),
                        OB if row.last_kind == "ob" else PB,
                    )
            elif name == "tyre" and c.tyre_compound:
                tyre_dot(p, c.tyre_compound, x + w / 2, y + rh / 2, 0.38 * fs)
            elif name == "ve" and c.energy is not None:
                e = max(0.0, min(1.0, c.energy))
                col = GAIN if e > 0.3 else (ORANGE if e > 0.12 else RED)
                p.fillRect(QRectF(x + pad, y + rh * 0.2, 3.5 * s, rh * 0.6), col)
                p.setFont(ov_font(fs * 0.95))
                text(p, x, y, w - pad, rh, f"{e * 100:.0f}%", WHITE, RIGHT)
            elif name == "pit":
                self._pit_cell(p, c, row.stint, x, y, w, rh)
            elif name == "stops":
                p.setFont(ov_font(fs))
                text(p, x, y, w - pad, rh, str(c.pit_stops), WHITE, RIGHT)
            elif name in ("t1", "t2", "t3") and row.trend:
                v = row.trend[["t1", "t2", "t3"].index(name)]
                if v is not None and abs(v) < 30:
                    p.setFont(ov_font(fs))
                    text(p, x, y, w - pad, rh, f"{abs(v):.1f}", GAIN if v > 0 else LOSS, RIGHT)
            x += w

    def _pit_cell(self, p: QPainter, c: CarState, stint: int, x, y, w, rh) -> None:
        s, fs = self.scale, self.fs
        p.setFont(ov_font(fs))
        if c.in_pits or c.pit_state in (PitState.STEHT, PitState.EINFAHRT, PitState.AUSFAHRT):
            p.fillRect(
                QRectF(x + 2 * s, y + 2 * s, w - 4 * s, rh - 4 * s), QColor(200, 150, 0, 220)
            )
            text(p, x, y, w, rh, "PIT", QColor("#111"), CENTER)
        elif c.pit_state == PitState.ANGEFORDERT:
            text(p, x + 3 * s, y, w, rh, "BOX", ORANGE)
        else:
            p.setFont(ov_font(fs * 0.7))
            text(p, x + 3 * s, y, w, rh, "PIT", DIM)
            p.setFont(ov_font(fs))
            text(p, x, y, w - 4 * s, rh, str(stint), WHITE, RIGHT)

    @staticmethod
    def _chevron(p: QPainter, cx, cy, r, up: bool, col: QColor) -> None:
        p.setPen(
            QPen(
                col,
                r * 0.55,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )
        d = -1 if up else 1
        p.drawPolyline(
            QPolygonF(
                [
                    QPointF(cx - r, cy - d * r * 0.5),
                    QPointF(cx, cy + d * r * 0.5),
                    QPointF(cx + r, cy - d * r * 0.5),
                ]
            )
        )


# --- Relative -----------------------------------------------------------------


class RelativeOverlay(Overlay):
    key = "relative"
    title = "Relative"

    def __init__(self, scale: float = 1.0, logos: Logos | None = None) -> None:
        self.logos = logos or Logos(None)
        self._entries = []
        super().__init__(scale)

    @property
    def fs(self) -> float:
        return 16 * self.scale

    @property
    def rh(self) -> float:
        return 28 * self.scale

    def on_data(self) -> None:
        self._entries = (
            self.tracker.relative(self.state, 3, 3) if self.state and self.tracker else []
        )

    def preferred_size(self) -> tuple[float, float]:
        return 21 * self.fs, self.rh * (7 + 2.4)

    def paint_overlay(self, p: QPainter) -> None:
        st = self.state
        s, fs, rh = self.scale, self.fs, self.rh
        w = self.width()
        h = self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 27, 38, 225))
        p.drawRoundedRect(QRectF(0, 0, w, h), 6 * s, 6 * s)
        # Kopf: Temperaturen, eigene VE
        p.setFont(ov_font(fs))
        head = []
        if st.air_temp is not None:
            head.append(f"Luft {st.air_temp:.0f}°C")
        if st.track_temp is not None:
            head.append(f"Strecke {st.track_temp:.0f}°C")
        if st.player and st.player.energy is not None:
            head.append(f"VE {st.player.energy * 100:.1f}%")
        text(p, 12 * s, 0, w - 24 * s, rh * 1.2, "   ".join(head), WHITE)
        y = rh * 1.2
        for k, e in enumerate(self._entries):
            c = e.car
            if c.is_player:
                p.fillRect(QRectF(0, y, w, rh), QColor(200, 162, 74, 235))
                p.fillRect(QRectF(0, y, 5 * s, rh), YELLOW)
                col = WHITE
            else:
                p.fillRect(QRectF(0, y, w, rh), ROW_A if k % 2 == 0 else ROW_B)
                col = LOSS if e.lap_diff > 0 else (QColor("#7db7ff") if e.lap_diff < 0 else WHITE)
                if c.in_pits:
                    col = QColor(col.red(), col.green(), col.blue(), 140)
            p.setFont(ov_font(fs))
            text(p, 0, y, 2.6 * fs, rh, str(c.class_position), col, RIGHT)
            p.setFont(ov_font(fs, 600, italic=True))
            text(p, 2.9 * fs, y, 3.2 * fs, rh, f"#{c.number}", col, RIGHT)
            p.setFont(ov_font(fs))
            name_w = 9.5 * fs
            p.save()
            p.setClipRect(QRectF(6.5 * fs, y, name_w, rh))
            text(p, 6.5 * fs, y, name_w * 2, rh, c.driver, col)
            p.restore()
            if c.in_pits:
                p.setFont(ov_font(fs * 0.65, 700))
                text(p, 6.5 * fs + name_w - 2.2 * fs, y, 2.2 * fs, rh, "PIT", ORANGE, RIGHT)
            draw_logo(p, self.logos, c, 16.2 * fs, y, 2 * fs, rh)
            p.setFont(ov_font(fs))
            gap = "0.0" if c.is_player else f"{e.gap:+.1f}".replace("-", "−")
            text(p, 0, y, w - 10 * s, rh, gap, col, RIGHT)
            y += rh
        # Fuß: Runde, Restzeit
        me = st.player_car()
        p.setFont(ov_font(fs))
        if me is not None:
            text(p, 12 * s, y, w, rh * 1.2, f"Runde: {me.laps + 1}", WHITE)
        if st.time_remaining is not None:
            text(
                p, 0, y, w - 12 * s, rh * 1.2, f"Rest: {fmt_clock(st.time_remaining)}", WHITE, RIGHT
            )


# --- Delta --------------------------------------------------------------------


class DeltaOverlay(Overlay):
    key = "delta"
    title = "Delta"
    RANGE = 1.0  # ± Sekunden Skala

    def __init__(self, scale: float = 1.0) -> None:
        self._hist: deque[float] = deque(maxlen=8)
        super().__init__(scale)

    def preferred_size(self) -> tuple[float, float]:
        return 330 * self.scale, 112 * self.scale

    def on_data(self) -> None:
        p = self.state.player if self.state else None
        if p is not None and p.delta_best is not None:
            self._hist.append(p.delta_best)

    def paint_overlay(self, p: QPainter) -> None:
        st = self.state
        s = self.scale
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 27, 38, 225))
        p.drawRoundedRect(QRectF(0, 0, w, h), 6 * s, 6 * s)
        me = st.player_car()
        pl = st.player
        d = pl.delta_best if pl else None
        best = me.best_lap if me else None
        valid = (
            d is not None and best is not None and me is not None and not me.in_pits and abs(d) < 60
        )
        if not valid:
            p.setFont(ov_font(26 * s, 700))
            text(p, 0, 6 * s, w, 40 * s, "–.–––", DIM, CENTER)
        else:
            col = GAIN if d < 0 else RED
            p.setFont(ov_font(30 * s, 700))
            text(p, 0, 4 * s, w, 40 * s, f"{d:+.3f}".replace("-", "−"), col, CENTER)
            # Pfeil: gewinne ich gerade Zeit?
            if len(self._hist) >= 2:
                gaining = self._hist[-1] < self._hist[0]
                cx = w / 2 + 70 * s
                cy = 24 * s
                r = 7 * s
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(GAIN if gaining else RED)
                dy = -1 if gaining else 1
                p.drawPolygon(
                    QPolygonF(
                        [
                            QPointF(cx - r, cy - dy * r * 0.7),
                            QPointF(cx + r, cy - dy * r * 0.7),
                            QPointF(cx, cy + dy * r * 0.8),
                        ]
                    )
                )
        # Balken
        bx, by, bw, bh = 12 * s, 48 * s, w - 24 * s, 9 * s
        p.fillRect(QRectF(bx, by, bw, bh), QColor(255, 255, 255, 30))
        mid = bx + bw / 2
        if valid:
            frac = max(-1.0, min(1.0, d / self.RANGE))
            # Schneller (negativ) wächst nach links
            length = -frac * bw / 2
            p.fillRect(QRectF(mid, by, -length, bh).normalized(), GAIN if d < 0 else RED)
        p.fillRect(QRectF(mid - 1 * s, by - 3 * s, 2 * s, bh + 6 * s), WHITE)
        p.setFont(ov_font(12 * s))
        text(p, 12 * s, 62 * s, w, 18 * s, f"Bestzeit {fmt_lap(best)}", WHITE)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawLine(QPointF(12 * s, 82 * s), QPointF(w - 12 * s, 82 * s))
        p.setFont(ov_font(11 * s, 700))
        text(p, 12 * s, 84 * s, w, 26 * s, "GESCHÄTZTE RUNDE", DIM)
        if valid:
            p.setFont(ov_font(22 * s, 700))
            text(p, 0, 84 * s, w - 12 * s, 26 * s, fmt_lap(best + d), GAIN if d < 0 else RED, RIGHT)


# --- Inputs -------------------------------------------------------------------


class InputsOverlay(Overlay):
    key = "inputs"
    title = "Inputs"
    WINDOW = 8.0  # Sekunden im Graphen

    def __init__(self, scale: float = 1.0) -> None:
        self._hist: deque[tuple[float, float, float, bool, bool]] = deque()
        super().__init__(scale)

    def preferred_size(self) -> tuple[float, float]:
        return 470 * self.scale, 110 * self.scale

    def on_data(self) -> None:
        st = self.state
        if st is None or st.player is None:
            return
        pl = st.player
        t = st.wall_time
        if self._hist and t < self._hist[-1][0]:
            self._hist.clear()
        if not self._hist or t > self._hist[-1][0]:
            self._hist.append((t, pl.throttle, pl.brake, pl.abs_active, bool(pl.tc_active)))
        while self._hist and self._hist[0][0] < t - self.WINDOW:
            self._hist.popleft()

    def paint_overlay(self, p: QPainter) -> None:
        st = self.state
        pl = st.player
        s = self.scale
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 27, 38, 225))
        p.drawRoundedRect(QRectF(0, 0, w, h), 6 * s, 6 * s)
        if pl is None:
            return
        # LED-Leisten: ABS gelb, TC blau
        led_w = 6 * s
        for i, on in enumerate((pl.abs_active, bool(pl.tc_active))):
            col = YELLOW if i == 0 else VE_BLUE
            lx = 6 * s if i == 0 else 6 * s + led_w + 2 * s
            p.fillRect(
                QRectF(lx, 10 * s, led_w, h - 20 * s), col if on else QColor(255, 255, 255, 25)
            )
        gx, gy, gw, gh = 26 * s, 10 * s, 300 * s, h - 20 * s
        p.fillRect(QRectF(gx, gy, gw, gh), QColor(255, 255, 255, 12))
        p.setPen(QPen(QColor(255, 255, 255, 25), 1))
        for q in (0.25, 0.5, 0.75):
            p.drawLine(QPointF(gx, gy + gh * q), QPointF(gx + gw, gy + gh * q))
        if len(self._hist) >= 2:
            t_end = self._hist[-1][0]

            def pt(t, v):
                return QPointF(gx + gw * (1 - (t_end - t) / self.WINDOW), gy + gh * (1 - v))

            for idx, col in ((1, QColor("#3ddc54")), (2, QColor("#ff4040"))):
                fill = QPolygonF([QPointF(pt(self._hist[0][0], 0))])
                for e in self._hist:
                    fill.append(pt(e[0], e[idx]))
                fill.append(pt(t_end, 0))
                fc = QColor(col)
                fc.setAlpha(45)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(fc)
                p.drawPolygon(fill)
                # Linie, Bremse gelb wo ABS eingreift
                prev = None
                for e in self._hist:
                    cur = pt(e[0], e[idx])
                    if prev is not None:
                        c = YELLOW if idx == 2 and e[3] else col
                        p.setPen(QPen(c, 2 * s))
                        p.drawLine(prev, cur)
                    prev = cur
        # Balken
        bx = gx + gw + 10 * s
        for i, (v, col) in enumerate(
            ((pl.brake, QColor("#ff4040")), (pl.throttle, QColor("#3ddc54")))
        ):
            x = bx + i * 22 * s
            p.fillRect(QRectF(x, gy, 16 * s, gh - 14 * s), QColor(255, 255, 255, 25))
            bh = (gh - 14 * s) * max(0.0, min(1.0, v))
            p.fillRect(
                QRectF(x, gy + gh - 14 * s - bh, 16 * s, bh),
                YELLOW if i == 0 and pl.abs_active else col,
            )
            p.setFont(ov_font(10 * s, 700))
            text(p, x - 4 * s, gy + gh - 13 * s, 24 * s, 13 * s, f"{v * 100:.0f}", WHITE, CENTER)
        # Lenkrad (falls Lenkung bekannt), Gang, Tempo
        cx = bx + 44 * s + (w - bx - 44 * s) / 2
        if pl.steering is not None:
            self._wheel(p, cx, 26 * s, 15 * s, pl.steering)
        gear = {-1: "R", 0: "N"}.get(pl.gear, str(pl.gear))
        p.setFont(ov_font(30 * s, 700))
        text(
            p,
            cx - 40 * s,
            38 * s if pl.steering is not None else 14 * s,
            80 * s,
            36 * s,
            gear,
            WHITE,
            CENTER,
        )
        p.setFont(ov_font(18 * s, 700))
        text(p, cx - 50 * s, 70 * s, 100 * s, 22 * s, f"{pl.speed_kmh:.0f}", WHITE, CENTER)
        p.setFont(ov_font(10 * s))
        text(p, cx - 50 * s, 88 * s, 100 * s, 14 * s, "km/h", DIM, CENTER)

    @staticmethod
    def _wheel(p: QPainter, cx, cy, r, steering: float) -> None:
        p.save()
        p.translate(cx, cy)
        p.rotate(steering * 270)  # ~540° Lenkbereich → halber Ausschlag
        p.setPen(QPen(WHITE, r * 0.28))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), r, r)
        p.drawLine(QPointF(-r, 0), QPointF(r, 0))
        p.drawLine(QPointF(0, 0), QPointF(0, r))
        p.restore()


# --- VE & Sprit ---------------------------------------------------------------


class EnergyOverlay(Overlay):
    key = "energie"
    title = "VE & Sprit"

    def __init__(self, scale: float = 1.0) -> None:
        self._ve = None
        self._fuel = None
        super().__init__(scale)

    def on_data(self) -> None:
        if self.state is None or self.tracker is None:
            self._ve = self._fuel = None
            return
        self._ve = energy_view(self.state, self.tracker, "energy")
        self._fuel = energy_view(self.state, self.tracker, "fuel")

    def preferred_size(self) -> tuple[float, float]:
        s = self.scale
        rows = (1 if self._ve else 0) + (1 if self._fuel else 0)
        main = self._ve or self._fuel
        box = 92 if main and main.allowed_per_lap is not None else 0
        return 340 * s, (14 + rows * 36 + box + 34) * s

    def paint_overlay(self, p: QPainter) -> None:
        s = self.scale
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 27, 38, 225))
        p.drawRoundedRect(QRectF(0, 0, w, h), 6 * s, 6 * s)
        y = 8 * s
        # Der knappere Wert bekommt den gelben Rand
        lim = None
        if self._ve and self._fuel and self._ve.laps_left and self._fuel.laps_left:
            lim = "energy" if self._ve.laps_left <= self._fuel.laps_left else "fuel"
        for v in (self._ve, self._fuel):
            if v is None:
                continue
            if lim == v.kind:
                p.fillRect(QRectF(4 * s, y, 3 * s, 30 * s), YELLOW)
            label = "VE" if v.kind == "energy" else "SPRIT"
            p.setFont(ov_font(12 * s))
            text(p, 12 * s, y, 60 * s, 30 * s, label, WHITE)
            frac = v.level / v.capacity if v.capacity else 0
            p.fillRect(QRectF(66 * s, y + 12 * s, 100 * s, 6 * s), QColor(255, 255, 255, 30))
            p.fillRect(
                QRectF(66 * s, y + 12 * s, 100 * s * max(0, min(1, frac)), 6 * s),
                VE_BLUE if v.kind == "energy" else ORANGE,
            )
            p.setFont(ov_font(19 * s, 700))
            val = f"{v.level * 100:.1f}" if v.kind == "energy" else f"{v.level:.1f}"
            unit = "%" if v.kind == "energy" else "L"
            text(p, 170 * s, y, 70 * s, 30 * s, val, WHITE, RIGHT)
            p.setFont(ov_font(11 * s))
            text(p, 242 * s, y + 3 * s, 20 * s, 30 * s, unit, DIM)
            p.setFont(ov_font(19 * s, 700))
            laps = f"{v.laps_left:.1f}" if v.laps_left is not None else "–"
            text(p, 250 * s, y, 66 * s, 30 * s, laps, WHITE, RIGHT)
            p.setFont(ov_font(11 * s))
            text(p, 318 * s, y + 3 * s, 20 * s, 30 * s, "Rd", DIM)
            y += 36 * s
        main = self._ve if lim != "fuel" and self._ve else self._fuel
        if main and main.allowed_per_lap is not None:
            ok = main.save_per_lap is not None and main.save_per_lap <= 0
            bg = QColor(40, 110, 60, 200) if ok else QColor(120, 40, 40, 200)
            edge = GAIN if ok else RED
            box = QRectF(10 * s, y, w - 20 * s, 84 * s)
            p.fillRect(box, bg)
            p.fillRect(QRectF(10 * s, y, 3 * s, 84 * s), edge)
            k = 100 if main.kind == "energy" else 1
            u = "%" if main.kind == "energy" else " L"
            name = "VE" if main.kind == "energy" else "SPRIT"
            p.setFont(ov_font(12 * s, 700))
            text(
                p,
                20 * s,
                y + 2 * s,
                w,
                18 * s,
                f"{name} PRO RUNDE · ZIEL {main.target_laps} RUNDEN",
                WHITE,
            )
            p.setFont(ov_font(11 * s))
            text(p, 20 * s, y + 20 * s, 140 * s, 14 * s, "Letzte Runde", DIM, CENTER)
            text(p, 170 * s, y + 20 * s, 140 * s, 14 * s, "Erlaubt (+1)", DIM, CENTER)
            p.setFont(ov_font(21 * s, 700))
            last = f"{main.last_lap * k:.2f}{u}" if main.last_lap is not None else "–"
            text(p, 20 * s, y + 34 * s, 140 * s, 26 * s, last, WHITE, CENTER)
            text(
                p,
                170 * s,
                y + 34 * s,
                140 * s,
                26 * s,
                f"{main.allowed_per_lap * k:.2f}{u}",
                edge,
                CENTER,
            )
            p.setFont(ov_font(13 * s, 700))
            if main.save_per_lap is not None:
                msg = (
                    f"▼ {main.save_per_lap * k:.2f}{u} pro Runde sparen"
                    if not ok
                    else f"✓ passt ({-main.save_per_lap * k:.2f}{u} Luft)"
                )
                text(p, 10 * s, y + 60 * s, w - 20 * s, 22 * s, msg, edge, CENTER)
            y += 92 * s
        # Letzte Runde
        p.setFont(ov_font(13 * s))
        text(p, 12 * s, y, w, 26 * s, "Letzte Runde", WHITE)
        parts = []
        if self._ve and self._ve.last_lap is not None:
            parts.append(f"{self._ve.last_lap * 100:.2f} %")
        if self._fuel and self._fuel.last_lap is not None:
            parts.append(f"{self._fuel.last_lap:.2f} L")
        text(p, 0, y, w - 12 * s, 26 * s, " · ".join(parts) or "–", WHITE, RIGHT)


ALL_OVERLAYS = (StandingsOverlay, RelativeOverlay, DeltaOverlay, InputsOverlay, EnergyOverlay)
