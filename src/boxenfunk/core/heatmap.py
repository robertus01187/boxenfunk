"""Farbstufen für Reifen- und Bremstemperaturen, wie TinyPedal.

Werte aus TinyPedal (GPLv3, github.com/TinyPedal/TinyPedal): ``setting/default_heatmap.py``
und ``setting/default_compounds.py``. Je Mischung eine eigene Skala (weich = TYRE_80,
mittel = TYRE_90, hart = TYRE_100, nass = TYRE_50). Die Farbe ist die der höchsten Stufe, die die
Temperatur erreicht hat (TinyPedal ``calc.select_grade``).
"""

from __future__ import annotations

import math

# Farbfolge von kalt nach heiß (blau → grün → gelb → rot)
_STEPS = ("#44F", "#48F", "#4FF", "#4F8", "#4F4", "#8F4", "#FF4", "#F84", "#F44")


def _tyre(optimal: int) -> tuple[tuple[float, str], ...]:
    # TYRE_80: -273, 50, 60, … 120 → optimal ist die 5. Stufe (grün #4F4)
    temps = [-273.0] + [optimal - 30 + 10 * i for i in range(8)]
    return tuple(zip(temps, _STEPS, strict=True))


TYRE_50 = _tyre(50)
TYRE_80 = _tyre(80)
TYRE_90 = _tyre(90)
TYRE_100 = _tyre(100)
BRAKE_400 = tuple(zip([-273.0] + [100.0 * i for i in range(1, 9)], _STEPS, strict=True))

# mCompoundType: 0 weich, 1 mittel, 2 hart, 3 nass
COMPOUND_HEATMAP = {0: TYRE_80, 1: TYRE_90, 2: TYRE_100, 3: TYRE_50}
COMPOUND_SYMBOL = {0: "S", 1: "M", 2: "H", 3: "W"}
COMPOUND_COLOR = {0: "#AAAAAA", 1: "#FFCC00", 2: "#EE2200", 3: "#00AAFF"}


def select_grade(scale: tuple[tuple[float, str], ...], value: float) -> str:
    """Farbe der höchsten erreichten Stufe."""
    if value is None or math.isnan(value):
        return "#888888"
    color = scale[0][1]
    for temp, col in scale:
        if value >= temp:
            color = col
        else:
            break
    return color


def tyre_color(compound_type: int, temp: float) -> str:
    return select_grade(COMPOUND_HEATMAP.get(compound_type, TYRE_80), temp)


def brake_color(temp: float) -> str:
    return select_grade(BRAKE_400, temp)
