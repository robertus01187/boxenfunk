"""Künstliches iRacing-Rennen für Tests.

``FakeIRacing`` simuliert ein Multiclass-Rennen (GT3 + LMP2, Pace-Car auf Slot 0).
- ``.ir`` verhält sich wie ``irsdk.IRSDK`` (für schnelle Tests ohne Datei),
- ``.dump(pfad)`` schreibt denselben Zustand als echtes iRacing-Speicherabbild, das ``pyirsdk``
  im Testmodus lesen kann (prüft den echten Lesepfad inkl. YAML).
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import yaml

TRACK_LEN = 7004.0
N = 64

# Name -> (Typ, Anzahl); Typen wie im iRacing-SDK: 1 bool, 2 int, 3 bitfield, 4 float, 5 double
VARS: dict[str, tuple[int, int]] = {
    "SessionTime": (5, 1),
    "SessionNum": (2, 1),
    "SessionState": (2, 1),
    "SessionFlags": (3, 1),
    "SessionTimeRemain": (5, 1),
    "SessionUniqueID": (2, 1),
    "PlayerCarIdx": (2, 1),
    "IsOnTrack": (1, 1),
    "IsReplayPlaying": (1, 1),
    "ReplayFrameNum": (2, 1),
    "FuelLevel": (4, 1),
    "LapLastLapTime": (4, 1),
    "LapBestLapTime": (4, 1),
    "Lap": (2, 1),
    "Speed": (4, 1),
    "AirTemp": (4, 1),
    "LFwearL": (4, 1),
    "LatAccel": (4, 1),
    "LatAccel_ST": (4, 6),
    "TestTireTemps": (4, 3),
    "CarIdxLap": (2, N),
    "CarIdxLapCompleted": (2, N),
    "CarIdxLapDistPct": (4, N),
    "CarIdxPosition": (2, N),
    "CarIdxClassPosition": (2, N),
    "CarIdxOnPitRoad": (1, N),
    "CarIdxTrackSurface": (2, N),
    "CarIdxLastLapTime": (4, N),
    "CarIdxBestLapTime": (4, N),
    "CarIdxEstTime": (4, N),
    "CarIdxClass": (2, N),
    "CarIdxRPM": (4, N),
}
FMT = {1: "?", 2: "i", 3: "I", 4: "f", 5: "d"}


def emit_yaml(sections: dict[str, Any]) -> str:
    """Session-Infos im iRacing-Stil (1 Leerzeichen Einrückung, Leerzeile zwischen Abschnitten)."""
    out = ["---"]
    for name, body in sections.items():
        text = yaml.safe_dump({name: body}, sort_keys=False, allow_unicode=True, indent=2)
        out.append(text.rstrip("\n"))
        out.append("")
    out.append("...")
    return "\n".join(out) + "\n"


class FakeIRacing:
    def __init__(self, n_gt3: int = 4, n_lmp2: int = 3, player_slot: int = 5) -> None:
        self.t = 0.0
        self.session_num = 0
        self.player = player_slot
        self.fuel = 60.0
        self.last_lap_time = -1.0
        self.best_lap_time = -1.0
        self.si_update = 1
        self.on_track = True
        self.cars: list[dict[str, Any]] = []
        for k in range(n_lmp2 + n_gt3):
            lmp2 = k < n_lmp2
            self.cars.append(
                {
                    "idx": k + 1,  # Slot 0 = Pace-Car
                    "cls": "LMP2" if lmp2 else "GT3",
                    "car": "Dallara P217" if lmp2 else f"GT3 Auto {k}",
                    "lap_time": (100.0 + k * 0.4) if lmp2 else (110.0 + k * 0.5),
                    "dist": TRACK_LEN * (0.98 - k * 0.03),
                    "laps": 0,
                    "last": -1.0,
                    "best": -1.0,
                    "pit_from": None,
                }
            )
        self.ir = FakeIR(self)

    # -- Simulation --
    def tick(self, dt: float) -> None:
        self.t += dt
        changed = False
        for c in self.cars:
            if c["pit_from"] is not None:
                if self.t - c["pit_from"] < 20:
                    continue
                c["pit_from"] = None
            c["dist"] += TRACK_LEN / c["lap_time"] * dt
            while c["dist"] >= TRACK_LEN:
                c["dist"] -= TRACK_LEN
                c["laps"] += 1
                c["last"] = c["lap_time"]
                c["best"] = c["lap_time"] if c["best"] < 0 else min(c["best"], c["lap_time"])
                changed = True
                if c["idx"] == self.player:
                    self.fuel -= 2.5
                    self.last_lap_time = c["lap_time"]
                    self.best_lap_time = c["best"]
                if c["idx"] == self.player and c["laps"] == 3:
                    c["pit_from"] = self.t  # eigener Boxenstopp nach Runde 3
                    self.fuel = 60.0
        if changed:
            self.si_update += 1

    def order(self) -> list[dict[str, Any]]:
        return sorted(self.cars, key=lambda c: -(c["laps"] * TRACK_LEN + c["dist"]))

    def values(self) -> dict[str, Any]:
        v: dict[str, Any] = {name: ([0] * cnt if cnt > 1 else 0) for name, (_, cnt) in VARS.items()}
        for name, (typ, cnt) in VARS.items():
            if typ in (4, 5):
                v[name] = [0.0] * cnt if cnt > 1 else 0.0
            if typ == 1:
                v[name] = [False] * cnt if cnt > 1 else False
        v["CarIdxTrackSurface"] = [-1] * N
        v["CarIdxLastLapTime"] = [-1.0] * N
        v["CarIdxBestLapTime"] = [-1.0] * N
        v.update(
            SessionTime=self.t,
            SessionNum=self.session_num,
            SessionState=4,
            SessionTimeRemain=3600.0 - self.t,
            SessionUniqueID=1,
            PlayerCarIdx=self.player,
            IsOnTrack=self.on_track,
            ReplayFrameNum=int(self.t * 60),
            FuelLevel=self.fuel,
            LapLastLapTime=self.last_lap_time,
            LapBestLapTime=self.best_lap_time,
            Speed=60.0,
            AirTemp=26.5,
            LFwearL=0.97,
            LatAccel=self.t % 3,
            TestTireTemps=[80.0, 81.0, 82.0],
        )
        v["CarIdxTrackSurface"][0] = 1  # Pace-Car in der Box
        class_count: dict[str, int] = {}
        for pos, c in enumerate(self.order(), start=1):
            i = c["idx"]
            class_count[c["cls"]] = class_count.get(c["cls"], 0) + 1
            in_pit = c["pit_from"] is not None
            v["CarIdxLap"][i] = c["laps"] + 1
            v["CarIdxLapCompleted"][i] = c["laps"]
            v["CarIdxLapDistPct"][i] = c["dist"] / TRACK_LEN
            v["CarIdxPosition"][i] = pos
            v["CarIdxClassPosition"][i] = class_count[c["cls"]]
            v["CarIdxOnPitRoad"][i] = in_pit
            v["CarIdxTrackSurface"][i] = 1 if in_pit else 3
            v["CarIdxLastLapTime"][i] = c["last"]
            v["CarIdxBestLapTime"][i] = c["best"]
            v["CarIdxEstTime"][i] = c["dist"] / TRACK_LEN * c["lap_time"]
            v["CarIdxClass"][i] = 4029 if c["cls"] == "LMP2" else 4074
            v["CarIdxRPM"][i] = 7000.0 + self.t % 100
        if self.player is not None:
            me = next(c for c in self.cars if c["idx"] == self.player)
            v["Lap"] = me["laps"] + 1
        return v

    def session_info(self) -> dict[str, Any]:
        drivers = [
            {
                "CarIdx": 0,
                "UserName": "Pace Car",
                "UserID": -1,
                "CarNumber": "0",
                "CarScreenName": "Safety Car",
                "CarClassShortName": "",
                "CarIsPaceCar": 1,
            }
        ]
        for c in self.cars:
            drivers.append(
                {
                    "CarIdx": c["idx"],
                    "UserName": "Robert Test" if c["idx"] == self.player else f"Fahrer {c['idx']}",
                    "UserID": 123456 + c["idx"],
                    "TeamName": f"Team {c['idx']}",
                    "CarNumber": str(c["idx"] * 7),
                    "CarScreenName": c["car"],
                    "CarScreenNameShort": c["car"].split()[0],
                    "CarClassShortName": c["cls"],
                    "CarIsPaceCar": 0,
                }
            )
        results = [
            {
                "Position": pos,
                "ClassPosition": pos - 1,
                "CarIdx": c["idx"],
                "Lap": c["laps"],
                "LapsComplete": c["laps"],
                "FastestTime": c["best"],
                "LastTime": c["last"],
            }
            for pos, c in enumerate(self.order(), start=1)
            if c["laps"] > 0
        ]
        return {
            "WeekendInfo": {
                "TrackName": "spa up",
                "TrackDisplayName": "Circuit de Spa-Francorchamps",
                "TrackConfigName": "Grand Prix Pits",
                "BuildVersion": "2026.11.10.01",
            },
            "SessionInfo": {
                "Sessions": [
                    {
                        "SessionNum": 0,
                        "SessionType": "Race",
                        "SessionName": "RACE",
                        "ResultsPositions": results or None,
                    }
                ]
            },
            "DriverInfo": {
                "DriverCarIdx": self.player,
                "DriverUserID": 123456 + self.player,
                "Drivers": drivers,
            },
        }

    # -- echtes Speicherabbild für pyirsdk --
    def dump(self, path: Path) -> Path:
        names = list(VARS)
        offsets, off = {}, 0
        for n in names:
            typ, cnt = VARS[n]
            offsets[n] = off
            off += struct.calcsize("<" + FMT[typ]) * cnt
        buf_len = off
        yaml_bytes = emit_yaml(self.session_info()).encode("latin-1") + b"\0"
        var_header_offset = 112
        si_offset = var_header_offset + 144 * len(names)
        buf_offset = si_offset + len(yaml_bytes)
        buf_offset += (-buf_offset) % 16

        mem = bytearray(buf_offset + buf_len)
        tick = int(self.t * 60) + 1
        struct.pack_into(
            "<iiiiiiiiiiiB",
            mem,
            0,
            2,  # version
            1,  # status: verbunden
            60,  # tick_rate
            self.si_update,
            len(yaml_bytes),
            si_offset,
            len(names),
            var_header_offset,
            1,  # num_buf
            buf_len,
            tick,
            0,
        )
        struct.pack_into("<iii", mem, 48, tick, buf_offset, tick)
        for k, n in enumerate(names):
            typ, cnt = VARS[n]
            struct.pack_into(
                "<iii?3x32s64s32s",
                mem,
                var_header_offset + k * 144,
                typ,
                offsets[n],
                cnt,
                False,
                n.encode(),
                b"",
                b"",
            )
        mem[si_offset : si_offset + len(yaml_bytes)] = yaml_bytes
        vals = self.values()
        for n in names:
            typ, cnt = VARS[n]
            val = vals[n] if cnt > 1 else [vals[n]]
            struct.pack_into("<" + FMT[typ] * cnt, mem, buf_offset + offsets[n], *val)
        path.write_bytes(bytes(mem))
        return path


class FakeIR:
    """Nachbau der von ``IRacingSource`` genutzten Teile von ``irsdk.IRSDK``."""

    def __init__(self, sim: FakeIRacing) -> None:
        self.sim = sim
        self.running = True
        self.is_initialized = False
        self.startups = 0
        self._frozen: dict[str, Any] = {}
        self._shared_mem = b"UserID: 123456\nfoo"

    @property
    def is_connected(self) -> bool:
        return self.is_initialized and self.running

    def startup(self, test_file: str | None = None) -> bool:
        self.startups += 1
        self.is_initialized = self.running
        return self.running

    def shutdown(self) -> None:
        self.is_initialized = False

    def freeze_var_buffer_latest(self) -> None:
        self._frozen = self.sim.values()

    @property
    def var_headers_names(self) -> list[str]:
        return list(VARS)

    @property
    def session_info_update(self) -> int:
        return self.sim.si_update

    def __getitem__(self, key: str) -> Any:
        if key in VARS:
            return self._frozen.get(key)
        return self.sim.session_info().get(key)
