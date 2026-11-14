"""Aufbereitung für die Anzeigen: welche Zeilen, welche Abstände, welcher Verbrauch.

Ohne Qt, damit es sich mit Aufnahmen testen lässt. Die Overlays zeichnen nur noch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from boxenfunk.core.tracker import SessionTracker
from boxenfunk.model.race_state import CarState, RaceState


@dataclass
class StandingsRow:
    car: CarState
    gap: str  # Abstand zum Klassenführenden, "+2L" bei Überrundung
    interval: str  # Abstand zum Auto davor in der Klasse
    gained: int | None
    last_kind: str  # "ob" = Klassenbestzeit, "pb" = eigene Bestzeit, "" sonst
    stint: int
    trend: list[float | None]
    gap_before: bool = False  # Lücke (ausgelassene Plätze) vor dieser Zeile


def gap_between(st: RaceState, car: CarState, ref: CarState) -> str:
    """Abstand von ``car`` hinter ``ref`` (ref liegt vorn), als Text.

    Liegt ``car`` eine Runde oder mehr zurück: "+1L". Sonst Summe der Abstände zum jeweils
    davor liegenden Auto (``gap_ahead``) über die Gesamtwertung, so wie das Spiel sie misst.
    """
    L = st.track_length or 1.0
    behind = (ref.laps + ref.lap_dist / L) - (car.laps + car.lap_dist / L)
    if behind >= 1.0:
        return f"+{int(behind)}L"
    total = 0.0
    for c in st.cars[ref.position : car.position]:
        if c.gap_ahead is None:
            return ""
        total += c.gap_ahead
    if total < 0:
        return ""
    return f"{total:.0f}" if total >= 100 else f"{total:.1f}"


def standings_blocks(
    st: RaceState,
    tr: SessionTracker,
    top: int = 3,
    around: int = 2,
    other_top: int = 3,
) -> list[tuple[str, list[StandingsRow]]]:
    """Je Klasse ein Block: Spitze + Autos um mich (eigene Klasse) bzw. nur Spitze (andere)."""
    me = st.player_car()
    blocks = []
    for cls in st.classes():
        cars = [c for c in st.cars if c.car_class == cls]
        if me is not None and cls == me.car_class:
            idx = next(i for i, c in enumerate(cars) if c.car_id == me.car_id)
            keep = set(range(min(top, len(cars))))
            lo = max(0, idx - around)
            hi = min(len(cars), idx + around + 1)
            # Am Ende der Klasse trotzdem gleich viele Zeilen zeigen
            while hi - lo < 2 * around + 1 and (lo > 0 or hi < len(cars)):
                if lo > 0:
                    lo -= 1
                else:
                    hi += 1
            keep |= set(range(lo, hi))
        else:
            if other_top <= 0:
                continue
            keep = set(range(min(other_top, len(cars))))
        rows: list[StandingsRow] = []
        prev = -1
        for i in sorted(keep):
            c = cars[i]
            leader = cars[0]
            ahead = cars[i - 1] if i > 0 else None
            if c.last_lap and c.last_lap == tr.best_lap_class.get(cls):
                kind = "ob"
            elif c.laps >= 2 and c.last_lap and c.best_lap and c.last_lap == c.best_lap:
                kind = "pb"
            else:
                kind = ""
            rows.append(
                StandingsRow(
                    car=c,
                    gap="" if i == 0 else gap_between(st, c, leader),
                    interval="" if ahead is None else gap_between(st, c, ahead),
                    gained=tr.positions_gained(c),
                    last_kind=kind,
                    stint=tr.stint_laps(c),
                    trend=[]
                    if c.is_player or (me and c.car_class != me.car_class)
                    else tr.trend(st, c),
                    gap_before=prev >= 0 and i != prev + 1,
                )
            )
            prev = i
        blocks.append((cls, rows))
    return blocks


@dataclass
class EnergyView:
    kind: str  # "energy" (VE, Anteil) oder "fuel" (Liter)
    level: float  # VE 0–1 bzw. Liter
    capacity: float | None
    avg_per_lap: float | None
    last_lap: float | None
    laps_left: float | None
    target_laps: int | None  # Ziel = eine Runde mehr als jetzt möglich
    allowed_per_lap: float | None
    save_per_lap: float | None  # positiv = so viel pro Runde sparen


def energy_view(
    st: RaceState, tr: SessionTracker, kind: str, avg_laps: int = 5
) -> EnergyView | None:
    p = st.player
    if p is None:
        return None
    level = p.energy if kind == "energy" else p.fuel
    if level is None or (kind == "energy" and level <= 0 and not tr.player.laps):
        return None
    cap = 1.0 if kind == "energy" else p.fuel_capacity
    avg = tr.usage_average(kind, avg_laps)
    last = tr.last_usage(kind)
    laps_left = level / avg if avg else None
    target = allowed = save = None
    if laps_left is not None:
        target = math.floor(laps_left) + 1
        allowed = level / target
        if last is not None:
            save = last - allowed
    return EnergyView(kind, level, cap, avg, last, laps_left, target, allowed, save)
