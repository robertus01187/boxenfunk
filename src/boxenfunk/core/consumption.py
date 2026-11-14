"""Verbrauch pro Runde (VE oder Sprit), Rechenweg wie TinyPedal.

Nachbau von ``calc_consumption`` aus TinyPedal (GPLv3, github.com/TinyPedal/TinyPedal,
``tinypedal/module/module_fuel.py``):

- Während der Runde wird mitgeschrieben, wie viel schon verbraucht ist (alle 5 m ein Punkt).
- Die letzte gültige Runde (nicht Box, gültige Rundenzeit) ist die Vorlage.
- Schätzung für die laufende Runde = Verbrauch der letzten gültigen Runde + Abweichung, die man
  gerade gegenüber dieser Runde an derselben Stelle hat. Sparst du, sinkt die Schätzung sofort.
- Runden Rest = aktueller Stand / Schätzung.

Nicht übernommen (noch): Speichern der Vorlage-Runde in eine Datei für die nächste Session.
"""

from __future__ import annotations

import bisect
import math

MIN_STEP = 5.0  # m zwischen zwei Messpunkten (TinyPedal: minimum_delta_distance)
LAP_START_WINDOW = 200.0  # m nach der Linie, in denen ein Rundenwechsel zählt
TELEPORT = 100.0  # m Sprung = zurückgesetzt (z. B. Garage)
VALIDATE_AFTER = 0.3  # s nach der Linie: ist die Rundenzeit gültig?
VALIDATE_MAX = 8.0


class Consumption:
    def __init__(self) -> None:
        self.curve_last: list[tuple[float, float]] = []  # Vorlage: (Meter, verbraucht)
        self._pos_last_curve: list[float] = []
        self.used_last_valid: float | None = None  # Verbrauch der letzten gültigen Runde
        self.used_last_raw: float | None = None  # Verbrauch der letzten Runde (egal ob gültig)
        self.delta = 0.0  # Abweichung zur Vorlage an derselben Stelle (+ = mehr verbraucht)
        self.used_curr = 0.0  # in dieser Runde bisher verbraucht
        self._raw: list[tuple[float, float]] = [(0.0, 0.0)]
        self._tmp: list[tuple[float, float]] | None = None
        self._tmp_used: float | None = None
        self._amount_start = -math.inf
        self._amount_last = 0.0
        self._lap_no: int | None = None
        self._pos_recorded = 0.0
        self._pos_last = 0.0
        self._recording = False
        self._validating: float | None = None
        self._pit_lap = True  # erste Runde zählt nie

    @property
    def estimate(self) -> float | None:
        """Geschätzter Verbrauch dieser Runde (TinyPedal ``estimatedValidConsumption``)."""
        if self.used_last_valid is None:
            return None
        if self._pit_lap:
            return self.used_last_valid
        return self.used_last_valid + self.delta

    def laps_left(self, amount: float) -> float | None:
        est = self.estimate
        if est is None or est <= 0:
            return None
        return amount / est

    def update(
        self,
        amount: float | None,
        lap_no: int,
        lap_dist: float,
        now: float,
        speed: float,
        in_pits: bool,
        in_garage: bool,
        last_lap_valid: bool,
    ) -> None:
        if amount is None:
            return
        self._pit_lap = self._pit_lap or in_pits

        # Verbrauch seit Rundenbeginn; Nachtanken an der Box setzt neu an
        if self._amount_start < amount:
            self._amount_start = self._amount_last = amount
        diff = self._amount_last - amount
        if self._amount_last < amount:
            if speed > 1:  # Rückgewinnung während der Fahrt
                self.used_curr += diff
            else:  # Nachtanken
                self._amount_start = amount
            self._amount_last = amount
        elif self._amount_last > amount:
            self.used_curr += diff
            self._amount_last = amount

        # Rundenwechsel
        if self._lap_no != lap_no and 0 < lap_dist < LAP_START_WINDOW:
            if (
                not self._pit_lap
                and self._lap_no is not None
                and self._lap_no < lap_no
                and len(self._raw) >= 10
            ):
                self._raw.append((self._raw[-1][0] + 10, self.used_curr))
                self._tmp = self._raw
                self._tmp_used = self.used_curr
                self._validating = now
            self._raw = [(0.0, 0.0)]
            self._pos_last = self._pos_recorded = lap_dist
            self.used_last_raw = self.used_curr if self._lap_no is not None else None
            self.used_curr = 0.0
            self._recording = True
            self._pit_lap = in_pits
            self._lap_no = lap_no

        # Messpunkte mitschreiben
        if lap_dist >= 0 and lap_dist != self._pos_last:
            if self._recording:
                step = lap_dist - self._pos_recorded
                if step > TELEPORT:
                    self._recording = False
                    self._raw = [(0.0, 0.0)]
                elif step >= MIN_STEP:
                    self._raw.append((lap_dist, self.used_curr))
                    self._pos_recorded = lap_dist
            self._pos_last = lap_dist

        # Kurz nach der Linie: war die Runde gültig? Dann wird sie die neue Vorlage
        if self._validating is not None:
            t = now - self._validating
            if t > VALIDATE_MAX or t < 0:
                self._validating = None
            elif t > VALIDATE_AFTER and last_lap_valid and self._tmp is not None:
                self.curve_last = self._tmp
                self._pos_last_curve = [p for p, _ in self._tmp]
                self.used_last_valid = self._tmp_used
                self._tmp = None
                self._validating = None

        # Abweichung zur Vorlage an derselben Stelle
        self.delta = 0.0
        if self.curve_last and not in_garage:
            i = bisect.bisect_left(self._pos_last_curve, lap_dist)
            if 0 < i < len(self.curve_last):
                (p0, u0), (p1, u1) = self.curve_last[i - 1], self.curve_last[i]
                ref = u0 + (u1 - u0) * (lap_dist - p0) / (p1 - p0) if p1 != p0 else u0
                self.delta = self.used_curr - ref
