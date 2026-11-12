"""Künstliches LMU-Rennen für Tests: füllt die echte LMU-Datenstruktur mit plausiblen Werten."""

from __future__ import annotations

from boxenfunk.adapters.lmu import lmu_data as d

TRACK_LEN = 5412.0


class FakeLmu:
    """Simuliertes Multiclass-Rennen. ``tick(dt)`` lässt die Zeit laufen."""

    def __init__(self, n_hyper: int = 3, n_gt3: int = 4, player_index: int = 4) -> None:
        self.data = d.LMUObjectOut()
        self.cars = []
        for i in range(n_hyper + n_gt3):
            hyper = i < n_hyper
            self.cars.append(
                {
                    "id": 10 + i,
                    "cls": "Hyper" if hyper else "GT3",
                    "lap_time": 110.0 + i * 0.5 if hyper else 122.0 + (i - n_hyper) * 0.6,
                    "dist": TRACK_LEN * (1 - i * 0.05),
                    "laps": 0,
                    "ve": 1.0,
                    "ve_per_lap": 0.06 if hyper else 0.07,
                    "player": i == player_index,
                    "pit_until": 0.0,
                    "stops": 0,
                }
            )
        self.et = 0.0
        self.data.generic.gameVersion = 1234
        si = self.data.scoring.scoringInfo
        si.mTrackName = b"Bahrain International Circuit"
        si.mSession = 10
        si.mLapDist = TRACK_LEN
        si.mGamePhase = 5
        si.mEndET = 8 * 3600
        self.data.generic.events.SME_UPDATE_SCORING = 1
        self.data.generic.events.SME_UPDATE_TELEMETRY = 1
        self._write()

    def update(self) -> bool:  # Source-Protokoll
        return True

    def tick(self, dt: float) -> None:
        self.et += dt
        for c in self.cars:
            if self.et < c["pit_until"]:
                continue
            if c.get("refill"):  # Stopp vorbei: aufgefüllt
                c["ve"] = 1.0
                c["refill"] = False
            c["dist"] += TRACK_LEN * dt / c["lap_time"]
            c["ve"] -= c["ve_per_lap"] * dt / c["lap_time"]
            while c["dist"] >= TRACK_LEN:
                c["dist"] -= TRACK_LEN
                c["laps"] += 1
                if c["ve"] < 0.15:  # Boxenstopp: 30 s stehen, volltanken
                    c["pit_until"] = self.et + 30.0
                    c["refill"] = True
                    c["stops"] += 1
        self._write()

    def _write(self) -> None:
        si = self.data.scoring.scoringInfo
        si.mCurrentET = self.et
        si.mNumVehicles = len(self.cars)
        self.data.telemetry.activeVehicles = len(self.cars)
        order = sorted(self.cars, key=lambda c: -(c["laps"] + c["dist"] / TRACK_LEN))
        place = {c["id"]: n + 1 for n, c in enumerate(order)}
        for i, c in enumerate(self.cars):
            v = self.data.scoring.vehScoringInfo[i]
            v.mID = c["id"]
            v.mDriverName = f"Fahrer {c['id']}".encode()
            v.mVehicleName = f"#{c['id']} {c['cls']}".encode()
            v.mVehicleClass = c["cls"].encode()
            v.mTotalLaps = c["laps"]
            v.mLapDist = c["dist"]
            v.mPlace = place[c["id"]]
            v.mIsPlayer = c["player"]
            v.mInPits = self.et < c["pit_until"]
            v.mNumPitstops = c["stops"]
            v.mLastLapTime = c["lap_time"] if c["laps"] else -1.0
            v.mBestLapTime = c["lap_time"] if c["laps"] else -1.0
            v.mSteamID = 76561190000000000 + c["id"]
            t = self.data.telemetry.telemInfo[len(self.cars) - 1 - i]  # andere Reihenfolge!
            t.mID = c["id"]
            t.mElapsedTime = self.et
            t.mVirtualEnergy = c["ve"]
            t.mFuel = 90.0 * c["ve"]
            t.mFuelCapacity = 90.0
            t.mLapNumber = c["laps"]
            t.mWheels[0].mWear = 0.97
        self.data.paths.userData = b"C:\\Users\\Geheim\\Documents"
