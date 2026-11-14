"""Übersetzt einen LMU-Momentzustand in das gemeinsame Datenmodell ``RaceState``.

Eingabe ist das Dict aus ``recorder.snapshot.snapshot()``. Genau dieses Dict liefert sowohl
der Live-Betrieb (Shared Memory) als auch das Abspielen einer Aufnahme (``DeltaDecoder``),
deshalb gilt dieselbe Übersetzung für beides.
"""

from __future__ import annotations

import math
import re
from typing import Any

from boxenfunk.model.race_state import (
    CarState,
    Phase,
    PitState,
    PlayerState,
    RaceState,
    SessionKind,
)

KELVIN = 273.15

# LMU mGamePhase (wie rFactor 2)
_PHASES = {
    0: Phase.GARAGE,
    1: Phase.GARAGE,
    2: Phase.GARAGE,
    3: Phase.FORMATION,
    4: Phase.FORMATION,
    5: Phase.GRUEN,
    6: Phase.GELB,
    7: Phase.ROT,
    8: Phase.ENDE,
    9: Phase.GRUEN,  # pausiert
}

_PIT = {
    0: PitState.KEINER,
    1: PitState.ANGEFORDERT,
    2: PitState.EINFAHRT,
    3: PitState.STEHT,
    4: PitState.AUSFAHRT,
    5: PitState.GARAGE,
}

# Erste Wörter von mVehicleModel → Marken-Schlüssel (wie die Logo-Namen im Design)
_BRANDS = {
    "mercedes-amg": "mercedes",
    "mercedes": "mercedes",
    "aston": "astonmartin",
    "chevrolet": "corvette",
    "corvette": "corvette",
    "isotta": "isotta",
    "glickenhaus": "glickenhaus",
    "scuderia": "glickenhaus",
}

_NAME_RE = re.compile(r"^(?P<team>.*?)\s*(?:\b(?:19|20)\d\d\b)?\s*#(?P<num>\d+)")


def session_kind(code: int) -> tuple[SessionKind, int]:
    if 1 <= code <= 4:
        return SessionKind.TRAINING, code
    if 5 <= code <= 8:
        return SessionKind.QUALI, code - 4
    if code == 9:
        return SessionKind.WARMUP, 1
    if 10 <= code <= 13:
        return SessionKind.RENNEN, code - 9
    if code == 0:
        return SessionKind.TRAINING, 0
    return SessionKind.UNBEKANNT, code


def brand_of(model: str) -> str:
    first = model.strip().split(" ", 1)[0].lower() if model.strip() else ""
    return _BRANDS.get(first, first.replace("-", ""))


def team_and_number(vehicle_name: str) -> tuple[str, str]:
    m = _NAME_RE.match(vehicle_name)
    if not m:
        return vehicle_name, ""
    return m.group("team").strip(), m.group("num")


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _lap_time(v: Any) -> float | None:
    """LMU meldet „keine Zeit“ als 0 oder negativ."""
    f = _num(v)
    return f if f is not None and f > 0 else None


def speed_kmh(vel: dict[str, float] | None) -> float:
    if not vel:
        return 0.0
    return 3.6 * math.sqrt(sum((vel.get(k) or 0.0) ** 2 for k in ("x", "y", "z")))


def _car(cid: str, c: dict[str, Any]) -> CarState:
    s = c.get("s", {})
    v = c.get("v", {})
    team, number = team_and_number(s.get("mVehicleName", ""))
    model = v.get("mVehicleModel", "") or ""
    fin = s.get("mFinishStatus", 0)
    return CarState(
        car_id=cid,
        driver=s.get("mDriverName", ""),
        number=number,
        team=team,
        model=model,
        brand=brand_of(model),
        car_class=s.get("mVehicleClass", ""),
        position=int(s.get("mPlace") or 0),
        laps=int(s.get("mTotalLaps") or 0),
        lap_dist=_num(s.get("mLapDist")) or 0.0,
        best_lap=_lap_time(s.get("mBestLapTime")),
        last_lap=_lap_time(s.get("mLastLapTime")),
        gap_leader=_num(s.get("mTimeBehindLeader")),
        laps_behind_leader=int(s.get("mLapsBehindLeader") or 0),
        gap_ahead=_num(s.get("mTimeBehindNext")),
        laps_behind_ahead=int(s.get("mLapsBehindNext") or 0),
        est_lap_time=_lap_time(s.get("mEstimatedLapTime")),
        in_pits=bool(s.get("mInPits")),
        pit_state=_PIT.get(s.get("mPitState", 0), PitState.KEINER),
        pit_stops=int(s.get("mNumPitstops") or 0),
        penalties=int(s.get("mNumPenalties") or 0),
        finished=fin == 1,
        dnf=fin in (2, 3),
        start_position=(s.get("mQualification") or None),
        energy=_num(v.get("mVirtualEnergy")),
        fuel=_num(v.get("mFuel")),
        fuel_capacity=_num(v.get("mFuelCapacity")),
        tyre_compound=v.get("mFrontTireCompoundName", "") or "",
        is_player=bool(s.get("mIsPlayer")),
    )


def _player(c: dict[str, Any]) -> PlayerState:
    s = c.get("s", {})
    v = c.get("v", {})
    wheels = v.get("mWheels") or []
    temps = []
    for w in wheels:
        t = [x for x in (w.get("mTemperature") or []) if x is not None]
        temps.append(sum(t) / len(t) - KELVIN if t else float("nan"))
    lap_start = _num(v.get("mLapStartET"))
    now = _num(v.get("mElapsedTime"))
    return PlayerState(
        throttle=_num(v.get("mFilteredThrottle")) or 0.0,
        brake=_num(v.get("mFilteredBrake")) or 0.0,
        clutch=_num(v.get("mFilteredClutch")),
        steering=_num(v.get("mFilteredSteering")),
        gear=int(v.get("mGear") or 0),
        speed_kmh=speed_kmh(v.get("mLocalVel") or s.get("mLocalVel")),
        rpm=_num(v.get("mEngineRPM")) or 0.0,
        rpm_max=_num(v.get("mEngineMaxRPM")) or 0.0,
        abs_active=bool(v.get("mABSActive")),
        tc_active=bool(v.get("mTCActive")) if "mTCActive" in v else None,
        delta_best=_num(v.get("mDeltaBest")),
        lap_time_current=(now - lap_start) if now is not None and lap_start is not None else None,
        lap_invalid=bool(v.get("mLapInvalidated")),
        energy=_num(v.get("mVirtualEnergy")),
        fuel=_num(v.get("mFuel")),
        fuel_capacity=_num(v.get("mFuelCapacity")),
        tyre_wear=[_num(w.get("mWear")) or 0.0 for w in wheels],
        tyre_temp=temps,
        tyre_compound=v.get("mFrontTireCompoundName", "") or "",
        track_limits_points=_num(v.get("mTrackLimitsSteps")),
        input_time=now,
    )


def to_race_state(snap: dict[str, Any]) -> RaceState:
    """Ein LMU-Momentzustand (Live oder aus Aufnahme) → ``RaceState``."""
    i = snap.get("i", {})
    kind, no = session_kind(int(i.get("mSession") or 0))
    end = _num(i.get("mEndET"))
    max_laps = i.get("mMaxLaps")
    cars: list[CarState] = []
    player = None
    player_id = None
    for cid, c in snap.get("c", {}).items():
        car = _car(cid, c)
        if car.position <= 0:
            continue
        cars.append(car)
        if car.is_player:
            player_id = cid
            player = _player(c)
    cars.sort(key=lambda c: c.position)
    per_class: dict[str, int] = {}
    for car in cars:
        per_class[car.car_class] = per_class.get(car.car_class, 0) + 1
        car.class_position = per_class[car.car_class]
    phase = _PHASES.get(int(i.get("mGamePhase") or 0), Phase.GARAGE)
    return RaceState(
        sim="LMU",
        wall_time=float(snap.get("t") or 0.0),
        session_kind=kind,
        session_no=no,
        session_time=_num(i.get("mCurrentET")) or 0.0,
        session_end=end if end and end > 0 else None,
        max_laps=max_laps if isinstance(max_laps, int) and 0 < max_laps < 100000 else None,
        phase=phase,
        track=i.get("mTrackName", ""),
        track_length=_num(i.get("mLapDist")) or 0.0,
        air_temp=_num(i.get("mAmbientTemp")),
        track_temp=_num(i.get("mTrackTemp")),
        wetness=_num(i.get("mAvgPathWetness")),
        rain=_num(i.get("mRaining")),
        cars=cars,
        player=player,
        player_id=player_id,
    )
