"""Wandelt die LMU-Shared-Memory-Daten in schlanke Python-Dicts um.

Aufgezeichnet wird fast alles, was für Standings, Relative, Sprit/VE und Strategie
gebraucht werden könnte. Weggelassen werden nur Werte, die sicher nicht gebraucht
werden und viel Platz kosten (Fahrwerks-Rohdaten, Drehmatrizen, Lenkrad-Rohwerte),
sowie persönliche Daten (Steam-IDs, Server-IP, Windows-Pfade).
"""

from __future__ import annotations

import ctypes
import math
from typing import Any

from boxenfunk.adapters.lmu import lmu_data as d

# --- Auswahl der Felder ------------------------------------------------------

SCORING_INFO_EXCLUDE = frozenset(
    {"mResultsStreamPointer", "mVehiclePointer", "mExpansion", "mServerPublicIP"}
)

VEH_SCORING_EXCLUDE = frozenset(
    {
        "mPos",
        "mOri",
        "mLocalRot",
        "mLocalRotAccel",
        "mLocalAccel",
        "mPathLateral",
        "mTrackEdge",
        "mUpgradePack",
        "mExpansion",
        "mSteamID",
    }
)

# Eigenes Auto: fast alles, ohne Fahrwerks-/Lenkungs-Rohdaten.
PLAYER_TELE_EXCLUDE = frozenset(
    {
        "mDeltaTime",
        "mPos",
        "mOri",
        "mLocalRot",
        "mLocalRotAccel",
        "mLocalAccel",
        "mUnfilteredThrottle",
        "mUnfilteredBrake",
        "mUnfilteredSteering",
        "mUnfilteredClutch",
        "mFilteredSteering",
        "mFilteredClutch",
        "mSteeringShaftTorque",
        "mFront3rdDeflection",
        "mRear3rdDeflection",
        "mFrontWingHeight",
        "mFrontRideHeight",
        "mRearRideHeight",
        "mDrag",
        "mFrontDownforce",
        "mRearDownforce",
        "mPhysicsToGraphicsOffset",
        "mUnused",
        "mExpansion",
    }
)

PLAYER_WHEEL_EXCLUDE = frozenset(
    {
        "mSuspensionDeflection",
        "mRideHeight",
        "mSuspForce",
        "mRotation",
        "mLateralPatchVel",
        "mLongitudinalPatchVel",
        "mLateralGroundVel",
        "mLongitudinalGroundVel",
        "mCamber",
        "mLateralForce",
        "mLongitudinalForce",
        "mTireLoad",
        "mGripFract",
        "mVerticalTireDeflection",
        "mWheelYLocation",
        "mToe",
        "mExpansion",
    }
)

# Gegner: nur Energie/Sprit, Reifen und ein paar Statuswerte.
OTHER_TELE_INCLUDE = (
    "mID",
    "mLapNumber",
    "mVehicleName",
    "mFuel",
    "mFuelCapacity",
    "mVirtualEnergy",
    "mBatteryChargeFraction",
    "mStateOfCharge",
    "mScheduledStops",
    "mCurrentSector",
    "mSpeedLimiter",
    "mHeadlights",
    "mDetached",
    "mDentSeverity",
    "mLastImpactET",
    "mFrontTireCompoundIndex",
    "mRearTireCompoundIndex",
    "mFrontTireCompoundName",
    "mRearTireCompoundName",
    "mVehicleModel",
    "mVehicleClass",
    "mVehicleChampionship",
)
OTHER_WHEEL_INCLUDE = ("mWear", "mFlat", "mDetached", "mCompoundIndex", "mCompoundType")

APP_INFO_INCLUDE = ("mWidth", "mHeight", "mWindowed", "mOptionsLocation", "mOptionsPage")


# --- Umwandlung ---------------------------------------------------------------


def num(v: float) -> float | None:
    """Rundet Kommazahlen platzsparend. Kleine Werte (z. B. Anteile 0–1) behalten mehr Stellen."""
    if math.isnan(v) or math.isinf(v):
        return None
    if abs(v) < 10:
        return round(v, 6)
    return round(v, 3)


def text(b: bytes) -> str:
    """C-Zeichenkette (nullterminiert) in str umwandeln."""
    return b.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def to_py(value: Any) -> Any:
    """Beliebigen ctypes-Wert (wie über Attributzugriff geliefert) in JSON-taugliche Werte umwandeln."""
    if isinstance(value, float):
        return num(value)
    if isinstance(value, bool | int):
        return int(value)
    if isinstance(value, bytes):
        return text(value)
    if isinstance(value, ctypes.Structure):
        return struct_to_dict(value)
    if isinstance(value, ctypes.Array):
        return [to_py(x) for x in value]
    return value


def struct_to_dict(
    s: ctypes.Structure,
    exclude: frozenset[str] = frozenset(),
    include: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    names = include if include is not None else [n for n, _ in s._fields_ if n not in exclude]
    return {n: to_py(getattr(s, n)) for n in names}


def scoring_info(si: d.LMUScoringInfo) -> dict[str, Any]:
    return struct_to_dict(si, SCORING_INFO_EXCLUDE)


def generic(g: d.LMUGeneric) -> dict[str, Any]:
    return {
        "gameVersion": g.gameVersion,
        "events": struct_to_dict(g.events),
        "appInfo": struct_to_dict(g.appInfo, include=APP_INFO_INCLUDE),
    }


def veh_scoring(v: d.LMUVehicleScoring) -> dict[str, Any]:
    return struct_to_dict(v, VEH_SCORING_EXCLUDE)


def veh_telemetry(t: d.LMUVehicleTelemetry, is_player: bool) -> dict[str, Any]:
    if is_player:
        out = struct_to_dict(t, PLAYER_TELE_EXCLUDE | {"mWheels"})
        out["mWheels"] = [struct_to_dict(w, PLAYER_WHEEL_EXCLUDE) for w in t.mWheels]
    else:
        out = struct_to_dict(t, include=OTHER_TELE_INCLUDE)
        out["mWheels"] = [struct_to_dict(w, include=OTHER_WHEEL_INCLUDE) for w in t.mWheels]
    return out


def snapshot(data: d.LMUObjectOut) -> dict[str, Any]:
    """Vollständiger Momentzustand: Session-Infos + alle aktiven Autos (Schlüssel = Slot-ID mID)."""
    scoring = data.scoring
    n_scor = max(0, min(scoring.scoringInfo.mNumVehicles, d.LMUConstants.MAX_MAPPED_VEHICLES))
    n_tele = max(0, min(data.telemetry.activeVehicles, d.LMUConstants.MAX_MAPPED_VEHICLES))

    tele_by_id = {}
    for i in range(n_tele):
        t = data.telemetry.telemInfo[i]
        tele_by_id[t.mID] = t

    cars: dict[str, dict[str, Any]] = {}
    for i in range(n_scor):
        v = scoring.vehScoringInfo[i]
        car: dict[str, Any] = {"s": veh_scoring(v)}
        t = tele_by_id.get(v.mID)
        if t is not None:
            car["v"] = veh_telemetry(t, bool(v.mIsPlayer))
        cars[str(v.mID)] = car

    return {
        "g": generic(data.generic),
        "i": scoring_info(scoring.scoringInfo),
        "tel": {
            "activeVehicles": data.telemetry.activeVehicles,
            "playerVehicleIdx": data.telemetry.playerVehicleIdx,
            "playerHasVehicle": int(data.telemetry.playerHasVehicle),
        },
        "c": cars,
    }


def anonymized_raw(data: d.LMUObjectOut) -> bytes:
    """Rohkopie des gesamten Speicherbereichs, ohne Windows-Pfade, Steam-IDs und Server-IP.

    Dient als Sicherheitsnetz: Falls sich die Datenstruktur als falsch herausstellt,
    lassen sich die Rohdaten später neu auswerten.
    """
    copy = d.LMUObjectOut.from_buffer_copy(bytes(data))
    ctypes.memset(ctypes.addressof(copy.paths), 0, ctypes.sizeof(copy.paths))
    copy.scoring.scoringInfo.mServerPublicIP = 0
    for v in copy.scoring.vehScoringInfo:
        v.mSteamID = 0
    return bytes(copy)
