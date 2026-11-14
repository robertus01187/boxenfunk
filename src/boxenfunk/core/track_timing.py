"""Echte Zeitabstände auf der Strecke (für Relative), gemessen statt geschätzt.

Idee wie eine Stoppuhr an jedem Streckenpunkt: Für jedes Auto merken wir uns, wann es welche
Stelle passiert hat. Der Abstand zum Auto vor mir ist dann „jetzt minus der Moment, als es an
meiner jetzigen Stelle war“; zum Auto hinter mir „jetzt minus der Moment, als ich an seiner
jetzigen Stelle war“. Das berücksichtigt, dass Autos in Kurven langsamer sind als auf Geraden.

Die frühere Schätzung (Streckenabstand × Rundenzeit) lag gegenüber den Spielwerten im Mittel
0,2 s und in jedem zehnten Fall über 0,7 s daneben (geprüft an einer Bahrain-Aufnahme).
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from boxenfunk.model.race_state import CarState, RaceState

KEEP_SECONDS = 400.0  # mehr als eine Runde, auch auf langen Strecken


@dataclass
class _Trace:
    dist: list[float] = field(default_factory=list)  # zurückgelegte Strecke gesamt (m), steigend
    time: list[float] = field(default_factory=list)  # Session-Zeit (s)
    last_lap_dist: float | None = None

    @property
    def total(self) -> float | None:
        return self.dist[-1] if self.dist else None

    def add(self, car: CarState, t: float, track_len: float) -> None:
        if self.last_lap_dist is None or not self.dist:
            total = car.laps * track_len + car.lap_dist
        else:
            step = car.lap_dist - self.last_lap_dist
            # Über Start/Ziel springt lap_dist von ~L auf ~0: wieder zusammensetzen
            if step < -track_len / 2:
                step += track_len
            elif step > track_len / 2:
                step -= track_len
            total = self.dist[-1] + step
        self.last_lap_dist = car.lap_dist
        if self.time and t <= self.time[-1]:
            return  # gleicher Messpunkt, nichts Neues
        if self.dist and total < self.dist[-1]:
            # Rückwärts (Garage, Zurücksetzen): Verlauf neu beginnen
            if self.dist[-1] - total > 50:
                self.dist.clear()
                self.time.clear()
            else:
                return
        self.dist.append(total)
        self.time.append(t)
        # Alte Werte abschneiden (gelegentlich, nicht bei jedem Punkt)
        if len(self.time) > 64 and self.time[0] < t - KEEP_SECONDS - 30:
            cut = bisect.bisect_left(self.time, t - KEEP_SECONDS)
            del self.dist[:cut]
            del self.time[:cut]

    def time_at(self, total: float) -> float | None:
        """Wann wurde die Gesamtstrecke ``total`` erreicht? (linear zwischen zwei Messpunkten)"""
        d = self.dist
        if len(d) < 2 or total < d[0] or total > d[-1]:
            return None
        i = bisect.bisect_left(d, total)
        if i == 0:
            return self.time[0]
        d0, d1 = d[i - 1], d[i]
        t0, t1 = self.time[i - 1], self.time[i]
        if d1 <= d0:
            return t1
        return t0 + (t1 - t0) * (total - d0) / (d1 - d0)


class TrackTiming:
    def __init__(self) -> None:
        self.traces: dict[str, _Trace] = {}

    def update(self, st: RaceState) -> None:
        if st.track_length <= 0:
            return
        for car in st.cars:
            self.traces.setdefault(car.car_id, _Trace()).add(car, st.session_time, st.track_length)

    def offset(self, st: RaceState, me: CarState, car: CarState) -> float:
        """Streckenabstand in Metern (positiv = Auto ist auf der Strecke vor mir)."""
        L = st.track_length
        d = car.lap_dist - me.lap_dist
        if d > L / 2:
            d -= L
        elif d < -L / 2:
            d += L
        return d

    def gap(self, st: RaceState, me: CarState, car: CarState) -> float | None:
        """Zeitabstand in Sekunden: negativ = Auto vor mir, positiv = hinter mir.

        None, wenn der Verlauf noch nicht reicht (z. B. gerade erst eingestiegen).
        """
        tm = self.traces.get(me.car_id)
        tc = self.traces.get(car.car_id)
        if tm is None or tc is None or tm.total is None or tc.total is None:
            return None
        d = self.offset(st, me, car)
        now = st.session_time
        if d >= 0:
            # Auto vor mir: wann war es dort, wo ich jetzt bin?
            t = tc.time_at(tc.total - d)
            return None if t is None else -(now - t)
        # Auto hinter mir: wann war ich dort, wo es jetzt ist?
        t = tm.time_at(tm.total + d)
        return None if t is None else now - t
