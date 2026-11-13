"""Wandelt die iRacing-Live-Daten in schlanke Python-Dicts um (gleiches Grundformat wie bei LMU).

Aufbau eines Momentzustands:
    g    Infos zur Datenquelle (SDK-Version, Takt)
    i    alle Einzelwerte (Session, Wetter, eigenes Auto: Sprit, Rundenzeiten, Reifen ...)
    tel  sonstige Listenwerte, die nicht pro Auto sind
    c    {CarIdx: {"s": Live-Werte des Autos (alle CarIdx*-Werte),
                   "v": Fahrer/Auto/Klasse aus den Session-Infos + "res" = Ergebniszeile}}
    si   (nur im Recorder, getrennt gespeichert) restliche Session-Infos: Strecke, Sessions, Wertung

Weggelassen werden nur Werte, die sicher nicht gebraucht werden und ständig wechseln
(Fahrwerks-Rohdaten, Lenkkraft, PC-Auslastung, 360-Hz-Teilwerte) sowie iRacing-Kundennummern.
"""

from __future__ import annotations

import math
from typing import Any

MAX_CARS = 64

EXCLUDE_VARS = frozenset(
    {
        "VelocityX",
        "VelocityY",
        "VelocityZ",
        "Yaw",
        "Pitch",
        "Roll",
        "YawNorth",
        "YawRate",
        "PitchRate",
        "RollRate",
        "LatAccel",
        "LongAccel",
        "VertAccel",
        "SteeringWheelAngle",
        "SteeringWheelTorque",
        "SteeringWheelPctTorque",
        "SteeringWheelPctTorqueSign",
        "SteeringWheelPctTorqueSignStops",
        "SteeringWheelPctDamper",
        "SteeringWheelPctIntensity",
        "SteeringWheelPctSmoothing",
        "SteeringWheelLimiter",
        "SteeringWheelPeakForceNm",
        "SteeringWheelMaxForceNm",
        "FrameRate",
        "CpuUsageFG",
        "CpuUsageBG",
        "GpuUsage",
        "ChanAvgLatency",
        "ChanLatency",
        "ChanQuality",
        "ChanPartnerQuality",
        "ChanClockSkew",
        "MemPageFaultSec",
        "MemSoftPageFaultsPerSec",
        "CarIdxRPM",
        "CarIdxSteer",
    }
)
EXCLUDE_SUFFIXES = ("_ST", "shockDefl", "shockVel", "rideHeight")

# Persönliche Kennungen, die nie gespeichert werden.
PRIVATE_KEYS = frozenset({"UserID", "DriverUserID"})


def num(v: float) -> float | None:
    if math.isnan(v) or math.isinf(v):
        return None
    if abs(v) < 10:
        return round(v, 6)
    return round(v, 3)


def to_py(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return num(value)
    if isinstance(value, bytes):
        return value.split(b"\0", 1)[0].decode("latin-1")
    if isinstance(value, list | tuple):
        return [to_py(x) for x in value]
    return value


def clean(obj: Any) -> Any:
    """Session-Infos JSON-tauglich machen und Kundennummern entfernen."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items() if k not in PRIVATE_KEYS}
    if isinstance(obj, list | tuple):
        return [clean(x) for x in obj]
    if isinstance(obj, float):
        return num(obj)
    if isinstance(obj, str | int | bool) or obj is None:
        return obj
    return str(obj)


def wanted(name: str) -> bool:
    return name not in EXCLUDE_VARS and not name.endswith(EXCLUDE_SUFFIXES)


def current_results(si: dict[str, Any], session_num: int | None) -> dict[int, dict[str, Any]]:
    """Ergebniszeilen (ResultsPositions) der laufenden Session, nach CarIdx."""
    for ses in (si.get("SessionInfo") or {}).get("Sessions") or []:
        if ses.get("SessionNum") == session_num:
            return {
                r["CarIdx"]: r
                for r in ses.get("ResultsPositions") or []
                if isinstance(r, dict) and "CarIdx" in r
            }
    return {}


def session_rest(si: dict[str, Any]) -> dict[str, Any]:
    """Session-Infos ohne die Teile, die schon pro Auto gespeichert werden (Fahrerliste, Ergebnisse)."""
    out: dict[str, Any] = {}
    for sec, val in si.items():
        if sec == "DriverInfo" and isinstance(val, dict):
            val = {k: v for k, v in val.items() if k != "Drivers"}
        elif sec == "SessionInfo" and isinstance(val, dict):
            val = dict(val)
            val["Sessions"] = [
                {k: v for k, v in s.items() if k != "ResultsPositions"}
                for s in val.get("Sessions") or []
                if isinstance(s, dict)
            ]
        out[sec] = val
    return clean(out)


def snapshot(src: Any) -> dict[str, Any]:
    """Vollständiger Momentzustand aus einer ``IRacingSource`` (oder etwas mit gleicher Schnittstelle)."""
    scalars: dict[str, Any] = {}
    arrays: dict[str, Any] = {}
    per_car: dict[str, list[Any]] = {}
    for name in src.var_names():
        if not wanted(name):
            continue
        val = src.get(name)
        if name.startswith("CarIdx") and isinstance(val, list):
            per_car[name] = val
        elif isinstance(val, list):
            arrays[name] = to_py(val)
        else:
            scalars[name] = to_py(val)

    si = src.session_info()
    drivers = {
        d["CarIdx"]: d
        for d in (si.get("DriverInfo") or {}).get("Drivers") or []
        if isinstance(d, dict) and "CarIdx" in d
    }
    results = current_results(si, scalars.get("SessionNum"))

    if drivers:
        idxs = sorted(i for i in drivers if 0 <= i < MAX_CARS)
    else:  # Fahrerliste fehlt noch: alle Autos nehmen, die irgendwo auf der Strecke sind
        surf = per_car.get("CarIdxTrackSurface") or []
        idxs = [i for i, s in enumerate(surf) if s != -1]

    cars: dict[str, dict[str, Any]] = {}
    for i in idxs:
        s = {n: to_py(vals[i]) for n, vals in per_car.items() if i < len(vals)}
        v = clean(drivers.get(i, {}))
        if i in results:
            v["res"] = clean(results[i])
        cars[str(i)] = {"s": s, "v": v}

    return {
        "g": {"sim": "iRacing"},
        "i": scalars,
        "tel": arrays,
        "c": cars,
    }
