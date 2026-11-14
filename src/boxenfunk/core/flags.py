"""Welche Flaggen gerade gelten, mit Abstand (Gelb) und Klasse des Überrundenden (Blau).

Rechenweg wie im Flaggen-Widget von TinyPedal (GPLv3, github.com/TinyPedal/TinyPedal,
``widget/flag.py`` und ``module/module_vehicles.py``):

- Gelb: Das Spiel meldet Gelb in einem Sektor. Gezeigt wird der Abstand in Metern zum nächsten
  langsamen Auto (unter 8 m/s, nicht in der Garage): bis 500 m vor mir, sonst bis 50 m hinter mir.
  Steht kein langsames Auto in diesem Bereich, bleibt die Flagge aus.
- Blau: Das Spiel zeigt mir Blau. Die Klasse ist die des nächsten Autos hinter mir (nach der vom
  Spiel geschätzten Zeit), das nicht in der Box ist und, im Rennen, mich überrundet (oder aus
  einer anderen Klasse kommt).
- Sprit/VE knapp: höchstens 2 Runden Rest.
- Grün: 3 s nach dem Start (TinyPedal), 5 s nach dem Ende einer Gelbphase (Design).
"""

from __future__ import annotations

from dataclasses import dataclass

from boxenfunk.core.tracker import SessionTracker, _game_gap
from boxenfunk.core.views import energy_view
from boxenfunk.model.race_state import CarState, Phase, PitState, RaceState, SessionKind

SLOW_SPEED = 8.0  # m/s, darunter gilt ein Auto als Gefahr (TinyPedal)
YELLOW_AHEAD = 500.0  # m
YELLOW_BEHIND = 50.0  # m
LOW_LAPS = 2.0
GREEN_START = 3.0  # s
GREEN_AFTER_YELLOW = 5.0  # s

# Reihenfolge = Wichtigkeit (oben im Stapel zuerst), wie im Flaggen-Muster
ORDER = ("ziel", "fcy", "gelb", "blau", "sprit", "pit", "gruen")


@dataclass
class Flag:
    kind: str  # einer aus ORDER
    name: str  # großes Wort links, z. B. "GELB"
    info: str = ""  # rechts, z. B. "▲ 230 m"


def class_label(cls: str) -> str:
    """Klassenname kurz und einheitlich: HYPERCAR, LMP2, LMP3, GT3, GTE."""
    c = cls.upper().replace(" ", "")
    if "HYPER" in c:
        return "HYPERCAR"
    for k in ("LMP2", "LMP3", "GTE", "GT3"):
        if k in c:
            return k
    return cls.upper() or "?"


def circular_relative(length: float, mine: float, theirs: float) -> float:
    """Streckenabstand, positiv = vor mir (TinyPedal ``circular_position_relative``)."""
    rel = theirs - mine
    if abs(rel) > length * 0.5:
        if theirs > mine:
            rel -= length
        elif theirs < mine:
            rel += length
    return rel


def _progress(car: CarState, length: float) -> float:
    return car.laps + (car.lap_dist / length if length > 0 else 0.0)


class FlagState:
    """Merkt sich, was für Zeitgeber nötig ist (Grün nach Gelb, Start)."""

    def __init__(self) -> None:
        self._prev_phase: Phase | None = None
        self._prev_yellow = False
        self._green_until: float | None = None

    def update(self, st: RaceState, tr: SessionTracker | None) -> list[Flag]:
        me = st.player_car()
        if me is None:
            return []
        now = st.session_time
        race = st.session_kind == SessionKind.RENNEN
        L = st.track_length
        flags: list[Flag] = []

        if me.finished:
            flags.append(Flag("ziel", "ZIEL", f"P{me.class_position} in der Klasse"))
        elif me.dnf:
            flags.append(Flag("ziel", "AUS", ""))

        fcy = st.phase == Phase.GELB
        yellow_shown = fcy
        if fcy:
            flags.append(Flag("fcy", "GELB", "ganze Strecke"))
        elif st.sector_yellow and L > 0:
            dist = self._yellow_distance(st, me)
            if dist is not None:
                yellow_shown = True
                if abs(dist) < 1:
                    info = "bei dir"
                else:
                    info = f"{'▲' if dist > 0 else '▼'} {abs(dist):.0f} m"
                flags.append(Flag("gelb", "GELB", info))

        if me.blue_flag:
            cls, gap = self._blue_from(st, me, race)
            info = cls or ""
            if gap is not None:
                info = f"{info}  ▼ {gap:.1f} s".strip()
            flags.append(Flag("blau", "BLAU", info))

        if tr is not None:
            low = None
            for kind, label in (("energy", "VE"), ("fuel", "SPRIT")):
                v = energy_view(st, tr, kind)
                if v is None or v.laps_left is None or v.laps_left > LOW_LAPS:
                    continue
                if low is None or v.laps_left < low[1]:
                    low = (label, v.laps_left)
            if low is not None:
                flags.append(Flag("sprit", low[0], f"noch {low[1]:.1f} Rd"))

        if me.pit_state == PitState.ANGEFORDERT:
            flags.append(Flag("pit", "BOX", "Stopp angefordert"))

        # Grün: kurz nach dem Start und nach dem Ende einer gezeigten Gelbphase
        yellow_now = yellow_shown
        if race and self._prev_phase == Phase.FORMATION and st.phase == Phase.GRUEN:
            self._green_until = now + GREEN_START
        elif self._prev_yellow and not yellow_now:
            self._green_until = now + GREEN_AFTER_YELLOW
        if yellow_now or (self._green_until is not None and now > self._green_until):
            self._green_until = None
        if self._green_until is not None:
            flags.append(Flag("gruen", "GRÜN", "Strecke frei"))
        self._prev_phase = st.phase
        self._prev_yellow = yellow_now

        flags.sort(key=lambda f: ORDER.index(f.kind))
        return flags

    @staticmethod
    def _yellow_distance(st: RaceState, me: CarState) -> float | None:
        L = st.track_length
        if me.speed < SLOW_SPEED and not me.in_garage:
            return 0.0
        ahead = YELLOW_AHEAD + 1
        behind = -(YELLOW_BEHIND + 1)
        for c in st.cars:
            if c.car_id == me.car_id or c.in_garage or c.speed >= SLOW_SPEED:
                continue
            d = circular_relative(L, me.lap_dist, c.lap_dist)
            if 0 <= d < ahead:
                ahead = d
            if behind < d <= 0:
                behind = d
        if ahead <= YELLOW_AHEAD:
            return ahead
        if behind >= -YELLOW_BEHIND:
            return behind
        return None

    @staticmethod
    def _blue_from(st: RaceState, me: CarState, race: bool) -> tuple[str, float | None]:
        L = st.track_length
        best: tuple[float, CarState] | None = None
        for c in st.cars:
            if c.car_id == me.car_id or c.in_pits:
                continue
            gap = _game_gap(me, c)  # positiv = hinter mir
            if gap is None or gap <= 0:
                continue
            if best is None or gap < best[0]:
                best = (gap, c)
        if best is None:
            return "", None
        gap, car = best
        # TinyPedal: im Rennen nur, wenn das Auto mich wirklich überrundet (eine Runde weiter).
        # Zusätzlich: ein Auto einer anderen Klasse direkt hinter mir ist immer gemeint.
        lapping = L > 0 and _progress(car, L) - _progress(me, L) >= 1
        if race and not lapping and car.car_class == me.car_class:
            return "", gap
        return class_label(car.car_class), gap
