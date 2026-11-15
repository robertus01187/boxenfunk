"""Aufbereitung für die Anzeigen: welche Zeilen, welche Abstände, welcher Verbrauch.

Ohne Qt, damit es sich mit Aufnahmen testen lässt. Die Overlays zeichnen nur noch.
"""

from __future__ import annotations

from dataclasses import dataclass

from boxenfunk.core.tracker import SessionTracker
from boxenfunk.model.race_state import CarState, PlayerState, RaceState, SessionKind


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

    Wie TinyPedal (``calc_time_gap_behind``): Mehr als eine Runde Rückstand → "+1L". Sonst
    Unterschied der vom Spiel geschätzten Zeit seit Start/Ziel; liegt ``car`` auf der Strecke
    scheinbar vorn, eine geschätzte Rundenzeit dazu. Fehlen die Werte: Summe der Abstände zum
    jeweils davor liegenden Auto, so wie das Spiel sie meldet.
    """
    L = st.track_length or 1.0
    behind = (ref.laps + ref.lap_dist / L) - (car.laps + car.lap_dist / L)
    if behind > 1.0:
        return f"+{int(behind)}L"
    if behind < 0:  # schon vorbei, Platz noch nicht umgestellt (TinyPedal zeigt dann 0)
        return "0.0"
    if ref.time_into_lap is not None and car.time_into_lap is not None and car.est_lap_time:
        total = ref.time_into_lap - car.time_into_lap
        if total < 0:
            total += car.est_lap_time
    else:
        total = 0.0
        for c in st.cars[ref.position : car.position]:
            if c.gap_ahead is None:
                return ""
            total += c.gap_ahead
    if total < 0:
        return ""
    return f"{total:.0f}" if total >= 100 else f"{total:.1f}"


def best_lap_gap(car: CarState, ref: CarState) -> str:
    """Training/Quali: Rückstand der Bestzeit auf ``ref`` (Rundenzahlen sind dort egal)."""
    if car.best_lap is None or ref.best_lap is None:
        return "–"
    d = car.best_lap - ref.best_lap
    return f"{d:.3f}" if d < 10 else f"{d:.1f}"


def standings_blocks(
    st: RaceState,
    tr: SessionTracker,
    top: int = 3,
    around: int = 2,
    other_top: int = 3,
    only_my_class: bool = False,
) -> list[tuple[str, list[StandingsRow]]]:
    """Je Klasse ein Block: Spitze + Autos um mich (eigene Klasse) bzw. nur Spitze (andere).

    ``only_my_class``: nur den Block der eigenen Klasse. Im Rennen zählen Abstände auf der
    Strecke, in Training und Quali der Rückstand der Bestzeit.
    """
    me = st.player_car()
    race = st.session_kind == SessionKind.RENNEN
    gap_fn = gap_between if race else (lambda _st, c, ref: best_lap_gap(c, ref))
    blocks = []
    for cls in st.classes():
        if only_my_class and me is not None and cls != me.car_class:
            continue
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
                    gap="" if i == 0 else gap_fn(st, c, leader),
                    interval="" if ahead is None else gap_fn(st, c, ahead),
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
    avg_per_lap: float | None  # Ø der letzten 5 sauberen Runden (Zusatzanzeige)
    last_lap: float | None  # Verbrauch der letzten Runde
    laps_left: float | None
    target_laps: int | None  # Ziel = eine Runde mehr als jetzt möglich
    allowed_per_lap: float | None
    save_per_lap: float | None  # positiv = so viel pro Runde sparen
    est_per_lap: float | None = None  # Schätzung dieser Runde (TinyPedal)


def energy_view(
    st: RaceState, tr: SessionTracker, kind: str, avg_laps: int = 5
) -> EnergyView | None:
    """VE- bzw. Sprit-Anzeige. Rechenweg wie TinyPedal (``module_fuel`` und
    ``widget/fuel_energy_saver``): Schätzung = letzte gültige Runde + Abweichung in dieser Runde,
    Ziel = eine Runde mehr ab dem Stand zu Beginn dieser Runde. Solange es noch keine gültige
    Runde gibt, gilt der Ø der letzten sauberen Runden."""
    p = st.player
    if p is None:
        me = st.player_car() if st.spectating else None
        if me is None or kind != "energy":
            return None  # beim Zuschauen kein Sprit (LMU liefert ihn dann nicht)
        p = PlayerState(energy=me.energy)
    level = p.energy if kind == "energy" else p.fuel
    if level is None or (kind == "energy" and level <= 0 and not tr.player.laps):
        return None
    cap = 1.0 if kind == "energy" else p.fuel_capacity
    avg = tr.usage_average(kind, avg_laps)
    cons = tr.consumption[kind]
    est = cons.estimate
    last = cons.used_last_raw if cons.used_last_raw else tr.last_usage(kind)
    used_now = cons.used_curr
    if est is None or est <= 0 or (st.spectating and avg):
        # Beim Zuschauen kommt VE nur in Schritten von 0,4 %: der Schnitt glättet das
        est, used_now = avg, 0.0
    laps_left = level / est if est else None
    target = allowed = save = None
    if est:
        at_lap_start = level + used_now
        target = int(round(at_lap_start / est, 1)) + 1
        allowed = at_lap_start / target
        save = est - allowed
    return EnergyView(kind, level, cap, avg, last, laps_left, target, allowed, save, est)
