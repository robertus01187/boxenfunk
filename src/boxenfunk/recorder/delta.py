"""Platzsparendes Speichern: pro Zeile nur das, was sich seit der letzten Zeile geändert hat.

Eine „Keyframe“-Zeile (k=1) enthält immer den vollständigen Zustand. Ab dort lässt sich
jede Datei unabhängig von vorherigen Dateien lesen.

Zeilenformat (JSON):
    t   Zeitstempel (Unix-Sekunden, Uhr des PCs)
    k   1 = Keyframe (vollständig)
    g/i/tel  geänderte Felder (generic / scoringInfo / telemetry-Kopf)
    c   {mID: {"s": geänderte Scoring-Felder, "v": geänderte Telemetrie-Felder}}
    x   Liste der mIDs, die verschwunden sind
"""

from __future__ import annotations

from typing import Any

SECTIONS = ("g", "i", "tel")
CAR_PARTS = ("s", "v")


def _diff(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    if not old:
        return dict(new)
    return {k: v for k, v in new.items() if old.get(k, _MISSING) != v}


_MISSING = object()


class DeltaEncoder:
    def __init__(self) -> None:
        self._last: dict[str, Any] | None = None

    def reset(self) -> None:
        """Nächste Zeile wird ein Keyframe."""
        self._last = None

    def encode(self, snap: dict[str, Any], t: float) -> dict[str, Any] | None:
        """Gibt die zu schreibende Zeile zurück, oder None, wenn sich nichts geändert hat."""
        last = self._last
        frame: dict[str, Any] = {"t": round(t, 3)}
        if last is None:
            frame["k"] = 1
        changed = False
        for sec in SECTIONS:
            delta = _diff(last[sec] if last else None, snap[sec])
            if delta:
                frame[sec] = delta
                changed = True

        cars_delta: dict[str, Any] = {}
        old_cars = last["c"] if last else {}
        for cid, car in snap["c"].items():
            old = old_cars.get(cid)
            cd = {}
            for part in CAR_PARTS:
                if part in car:
                    delta = _diff(old.get(part) if old else None, car[part])
                    if delta:
                        cd[part] = delta
            if cd:
                cars_delta[cid] = cd
        if cars_delta:
            frame["c"] = cars_delta
            changed = True
        gone = [cid for cid in old_cars if cid not in snap["c"]]
        if gone:
            frame["x"] = gone
            changed = True

        self._last = snap
        if not changed and last is not None:
            return None
        return frame


class DeltaDecoder:
    """Setzt aus Keyframe + Änderungszeilen wieder den vollständigen Zustand zusammen."""

    def __init__(self) -> None:
        self.state: dict[str, Any] | None = None

    def apply(self, frame: dict[str, Any]) -> dict[str, Any] | None:
        if frame.get("k"):
            self.state = {"g": {}, "i": {}, "tel": {}, "c": {}}
        if self.state is None:
            return None  # Anfang ohne Keyframe: noch kein vollständiger Zustand
        st = self.state
        st["t"] = frame["t"]
        for sec in SECTIONS:
            if sec in frame:
                st[sec].update(frame[sec])
        for cid, cd in frame.get("c", {}).items():
            car = st["c"].setdefault(cid, {})
            for part in CAR_PARTS:
                if part in cd:
                    car.setdefault(part, {}).update(cd[part])
        for cid in frame.get("x", []):
            st["c"].pop(cid, None)
        return st
