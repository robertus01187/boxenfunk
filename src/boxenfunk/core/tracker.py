"""Merkt sich, was über die Zeit passiert: Rundenzeiten aller Autos, Startplätze, eigener Verbrauch.

``RaceState`` ist nur eine Momentaufnahme. Für Trend (letzte 3 Runden), gewonnene Plätze und
Verbrauch pro Runde braucht es Geschichte; die sammelt der ``SessionTracker``.
Er kennt nur ``RaceState`` und funktioniert damit für alle Spiele gleich.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from boxenfunk.model.race_state import CarState, Phase, RaceState, SessionKind

HISTORY = 10  # gespeicherte Runden je Auto


@dataclass
class CarHistory:
    laps: deque[float | None] = field(default_factory=lambda: deque(maxlen=HISTORY))
    last_counted: int | None = None
    start_class_pos: int | None = None
    pit_this_lap: bool = False
    last_pit_lap: int | None = None


@dataclass
class LapUse:
    lap: int
    lap_time: float | None
    energy: float | None  # Verbrauch Anteil 0–1
    fuel: float | None  # Liter
    pit: bool


@dataclass
class PlayerHistory:
    laps: list[LapUse] = field(default_factory=list)
    lap_no: int | None = None
    energy_start: float | None = None
    fuel_start: float | None = None
    pit: bool = False


@dataclass
class RelativeEntry:
    car: CarState
    gap: float  # Sekunden auf der Strecke, negativ = vor mir
    lap_diff: int  # >0 = Auto liegt Runden vor mir, <0 = hinter mir


class SessionTracker:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.session_key: tuple | None = None
        self.last_time: float | None = None
        self.cars: dict[str, CarHistory] = {}
        self.player = PlayerHistory()
        self.best_lap_class: dict[str, float] = {}
        self.overall_best: float | None = None

    # -- Aktualisieren --

    def update(self, st: RaceState) -> None:
        key = (st.sim, st.session_kind, st.session_no, st.track)
        if key != self.session_key or (
            self.last_time is not None and st.session_time + 5 < self.last_time
        ):
            self.reset()
            self.session_key = key
        self.last_time = st.session_time

        race_running = st.session_kind == SessionKind.RENNEN and st.phase in (
            Phase.GRUEN,
            Phase.GELB,
            Phase.ENDE,
        )
        for car in st.cars:
            h = self.cars.setdefault(car.car_id, CarHistory())
            if h.start_class_pos is None and (
                race_running or st.session_kind != SessionKind.RENNEN
            ):
                h.start_class_pos = car.class_position
            if car.in_pits:
                h.pit_this_lap = True
                h.last_pit_lap = car.laps
            if h.last_counted is None:
                h.last_counted = car.laps
            elif car.laps > h.last_counted:
                h.laps.append(car.last_lap)
                h.last_counted = car.laps
                h.pit_this_lap = car.in_pits
            elif car.laps < h.last_counted:
                h.last_counted = car.laps
            if car.best_lap:
                cb = self.best_lap_class.get(car.car_class)
                if cb is None or car.best_lap < cb:
                    self.best_lap_class[car.car_class] = car.best_lap
                if self.overall_best is None or car.best_lap < self.overall_best:
                    self.overall_best = car.best_lap

        me = st.player_car()
        p = st.player
        if me is None or p is None:
            return
        ph = self.player
        if me.in_pits:
            ph.pit = True
        if ph.lap_no is None:
            ph.lap_no = me.laps
            ph.energy_start, ph.fuel_start = p.energy, p.fuel
            ph.pit = True  # angefangene Runde: zählt nicht für den Durchschnitt
        elif me.laps > ph.lap_no:
            e = _used(ph.energy_start, p.energy)
            f = _used(ph.fuel_start, p.fuel)
            ph.laps.append(LapUse(me.laps, me.last_lap, e, f, ph.pit))
            ph.lap_no = me.laps
            ph.energy_start, ph.fuel_start = p.energy, p.fuel
            ph.pit = me.in_pits
        elif me.laps < ph.lap_no:
            self.player = PlayerHistory(
                lap_no=me.laps, energy_start=p.energy, fuel_start=p.fuel, pit=True
            )

    # -- Abfragen --

    def positions_gained(self, car: CarState) -> int | None:
        h = self.cars.get(car.car_id)
        if h is None or h.start_class_pos is None:
            return None
        return h.start_class_pos - car.class_position

    def stint_laps(self, car: CarState) -> int:
        """Runden seit dem letzten Boxenbesuch (oder seit Beginn der Aufzeichnung)."""
        h = self.cars.get(car.car_id)
        if h is None or h.last_pit_lap is None:
            return car.laps
        return max(0, car.laps - h.last_pit_lap)

    def recent_laps(self, car_id: str, n: int = 3) -> list[float | None]:
        h = self.cars.get(car_id)
        if h is None:
            return []
        return list(h.laps)[-n:]

    def trend(self, st: RaceState, car: CarState, n: int = 3) -> list[float | None]:
        """Rundenzeit-Differenz zum eigenen Auto, älteste zuerst. Positiv = ich war schneller."""
        if st.player_id is None:
            return [None] * n
        mine = self.recent_laps(st.player_id, n)
        theirs = self.recent_laps(car.car_id, n)
        out: list[float | None] = []
        for k in range(n, 0, -1):
            a = theirs[-k] if len(theirs) >= k else None
            b = mine[-k] if len(mine) >= k else None
            out.append(a - b if a and b else None)
        return out

    def usage_average(self, kind: str, n: int = 5) -> float | None:
        """Ø-Verbrauch der letzten n sauberen Runden (ohne Box). kind = "energy" oder "fuel"."""
        vals = [
            getattr(lap, kind)
            for lap in self.player.laps
            if not lap.pit and getattr(lap, kind) is not None and getattr(lap, kind) > 0
        ]
        vals = vals[-n:]
        return sum(vals) / len(vals) if vals else None

    def last_usage(self, kind: str) -> float | None:
        for lap in reversed(self.player.laps):
            v = getattr(lap, kind)
            if not lap.pit and v is not None and v > 0:
                return v
        return None

    def relative(self, st: RaceState, ahead: int = 3, behind: int = 3) -> list[RelativeEntry]:
        """Autos auf der Strecke direkt vor und hinter mir (nach Streckenposition)."""
        me = st.player_car()
        if me is None or st.track_length <= 0:
            return []
        lap_t = me.est_lap_time or me.best_lap or 120.0
        L = st.track_length
        entries = []
        for car in st.cars:
            if car.car_id == me.car_id:
                entries.append(RelativeEntry(car, 0.0, 0))
                continue
            if car.pit_state.value == "garage":
                continue
            d = car.lap_dist - me.lap_dist
            if d > L / 2:
                d -= L
            elif d < -L / 2:
                d += L
            gap = -d / L * lap_t
            my_total = me.laps + me.lap_dist / L
            their_total = car.laps + car.lap_dist / L
            # Ganze Runden Unterschied, Streckenabstand herausgerechnet
            lap_diff = round(their_total - my_total - d / L)
            entries.append(RelativeEntry(car, gap, lap_diff))
        entries.sort(key=lambda e: e.gap)
        idx = next(i for i, e in enumerate(entries) if e.car.car_id == me.car_id)
        return entries[max(0, idx - ahead) : idx + behind + 1]


def _used(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return start - end
