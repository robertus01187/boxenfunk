"""Gemeinsames Datenmodell ``RaceState`` (ADR-001).

Alles hinter den Adaptern (Auswertung, Strategie, Overlays) kennt nur diese Klassen.
Spielspezifische Werte, die es nicht überall gibt (z. B. VE der Gegner nur in LMU),
sind optional (``None``), die Logik muss ohne sie auskommen.

Einheiten: Zeiten in Sekunden, Strecken in Metern, Tempo in km/h, Energie als Anteil 0–1,
Sprit in Litern, Temperaturen in °C.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SessionKind(StrEnum):
    TRAINING = "training"
    QUALI = "quali"
    WARMUP = "warmup"
    RENNEN = "rennen"
    UNBEKANNT = "unbekannt"


class Phase(StrEnum):
    """Zustand der Session, vereinfacht."""

    GARAGE = "garage"  # vor dem Start / Startaufstellung
    FORMATION = "formation"  # Einführungsrunde, Countdown
    GRUEN = "gruen"
    GELB = "gelb"  # Full Course Yellow / Safety Car
    ROT = "rot"
    ENDE = "ende"  # Karo-Flagge gezeigt / Session vorbei


class PitState(StrEnum):
    KEINER = ""
    ANGEFORDERT = "req"
    EINFAHRT = "in"
    STEHT = "stop"
    AUSFAHRT = "out"
    GARAGE = "garage"


@dataclass(slots=True)
class CarState:
    """Ein Auto im Feld (auch das eigene)."""

    car_id: str  # stabil innerhalb einer Session (LMU: Slot-ID mID)
    driver: str
    number: str  # Startnummer als Text, z. B. "51"
    team: str
    model: str  # z. B. "Porsche 911 GT3 R LMGT3"
    brand: str  # Kleinbuchstaben ohne Leerzeichen, z. B. "porsche", "" wenn unbekannt
    car_class: str  # z. B. "Hyper", "GT3"
    position: int  # Gesamtplatz (1 = vorn)
    class_position: int = 0
    laps: int = 0  # abgeschlossene Runden
    lap_dist: float = 0.0  # Meter seit Start/Ziel in der laufenden Runde
    best_lap: float | None = None
    last_lap: float | None = None
    gap_leader: float | None = None  # Sekunden hinter dem Gesamtführenden
    laps_behind_leader: int = 0
    gap_ahead: float | None = None  # Sekunden hinter dem Auto direkt davor (Gesamtwertung)
    laps_behind_ahead: int = 0
    est_lap_time: float | None = None
    in_pits: bool = False  # in der Boxengasse (inkl. Garage)
    in_garage: bool = False  # steht in der Garage (nicht auf der Strecke)
    pit_state: PitState = PitState.KEINER
    pit_stops: int = 0
    penalties: int = 0
    finished: bool = False
    dnf: bool = False
    start_position: int | None = None  # Startplatz laut Spiel (Gesamt)
    energy: float | None = None  # VE 0–1 (nur LMU Hypercar/GT3)
    fuel: float | None = None  # Liter
    fuel_capacity: float | None = None
    tyre_compound: str = ""  # z. B. "Medium"
    is_player: bool = False


@dataclass(slots=True)
class PlayerState:
    """Zusätzliche Werte nur fürs eigene Auto."""

    throttle: float = 0.0  # 0–1
    brake: float = 0.0  # 0–1
    clutch: float | None = None
    steering: float | None = None  # −1 … 1, None wenn nicht aufgezeichnet
    gear: int = 0  # −1 = R, 0 = N
    speed_kmh: float = 0.0
    rpm: float = 0.0
    rpm_max: float = 0.0
    abs_active: bool = False
    tc_active: bool | None = None  # None = Spiel meldet es nicht
    delta_best: float | None = None  # Sekunden zur eigenen Bestzeit (positiv = langsamer)
    lap_time_current: float | None = None  # Zeit in der laufenden Runde
    lap_invalid: bool = False
    energy: float | None = None
    fuel: float | None = None
    fuel_capacity: float | None = None
    tyre_wear: list[float] = field(default_factory=list)  # 4 Räder, 1 = neu
    tyre_temp: list[float] = field(default_factory=list)  # 4 Räder, Mittel der Lauffläche
    tyre_compound: str = ""
    track_limits_points: float | None = None
    gap_car_ahead: float | None = None  # vom Spiel: Sekunden zum Auto direkt vor mir (Strecke)
    gap_car_behind: float | None = None  # vom Spiel: Sekunden zum Auto direkt hinter mir
    input_time: float | None = None  # Spielzeit des letzten Eingabe-Messpunkts


@dataclass(slots=True)
class RaceState:
    """Momentaufnahme des ganzen Rennens."""

    sim: str  # "LMU" oder "iRacing"
    wall_time: float  # Uhr des PCs (Unix-Sekunden)
    session_kind: SessionKind
    session_no: int  # z. B. 1 für "Rennen 1"
    session_time: float  # Sekunden seit Session-Beginn
    session_end: float | None  # geplantes Ende (Sekunden) oder None bei Rundenrennen
    max_laps: int | None
    phase: Phase
    track: str
    track_length: float
    air_temp: float | None = None
    track_temp: float | None = None
    wetness: float | None = None  # 0 = trocken, 1 = nass
    rain: float | None = None
    cars: list[CarState] = field(default_factory=list)  # sortiert nach Gesamtplatz
    player: PlayerState | None = None
    player_id: str | None = None

    @property
    def time_remaining(self) -> float | None:
        if self.session_end is None:
            return None
        return max(0.0, self.session_end - self.session_time)

    def player_car(self) -> CarState | None:
        if self.player_id is None:
            return None
        return next((c for c in self.cars if c.car_id == self.player_id), None)

    def classes(self) -> list[str]:
        """Klassen in der Reihenfolge ihres besten Autos (schnellste Klasse zuerst)."""
        seen: list[str] = []
        for c in self.cars:
            if c.car_class not in seen:
                seen.append(c.car_class)
        return seen
