"""Auswertung einer iRacing-Aufnahme: Sessions, Endstand je Klasse, Rundenzeiten aller Autos,
Boxenbesuche und die eigenen Runden mit Spritverbrauch.

Dient zur Datenprüfung: Lassen sich aus der Aufnahme Standings, Relative, Rundenzeit-Vergleich
und Strategie-Werte rekonstruieren?
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from boxenfunk.recorder.delta import DeltaDecoder
from boxenfunk.recorder.files import read_lines, recording_files
from boxenfunk.recorder.iracing_recorder import session_label, track_name


@dataclass
class CarStats:
    idx: str
    name: str = ""
    number: str = ""
    car: str = ""
    car_make: str = ""
    cls: str = ""
    pace_car: bool = False
    player: bool = False
    place: int = 0
    class_place: int = 0
    laps: int = 0
    best: float | None = None
    lap_times: list[float] = field(default_factory=list)
    pit_entries: int = 0
    _last_lap_time: float | None = None
    _lap_seen: int | None = None
    _pending_since: float | None = None
    _pending_prev: float | None = None
    _on_pit: bool | None = None


@dataclass
class OwnLap:
    lap: int
    time: float | None
    fuel_start: float | None
    fuel_end: float | None
    pit: bool

    @property
    def fuel_used(self) -> float | None:
        if self.fuel_start is None or self.fuel_end is None:
            return None
        return self.fuel_start - self.fuel_end


@dataclass
class Session:
    num: int
    label: str
    track: str
    first_t: float
    last_t: float = 0.0
    frames: int = 0
    cars: dict[str, CarStats] = field(default_factory=dict)
    own_laps: list[OwnLap] = field(default_factory=list)
    _own_lap: int | None = None
    _own_fuel: float | None = None
    _own_pit: bool = False
    _own_llt: float | None = None
    _own_time_pending: float | None = None
    _own_pending_prev: float | None = None


def _update_cars(ses: Session, st: dict[str, Any]) -> None:
    player_idx = st["i"].get("PlayerCarIdx")
    for cid, c in st["c"].items():
        s, v = c.get("s", {}), c.get("v", {})
        cs = ses.cars.get(cid)
        if cs is None:
            cs = ses.cars[cid] = CarStats(idx=cid)
        cs.name = str(v.get("UserName") or cs.name)
        cs.number = str(v.get("CarNumber") or cs.number)
        cs.car = str(v.get("CarScreenName") or cs.car)
        cs.car_make = str(v.get("CarScreenNameShort") or cs.car_make)
        cs.cls = str(v.get("CarClassShortName") or cs.cls)
        cs.pace_car = bool(v.get("CarIsPaceCar"))
        cs.player = str(player_idx) == cid

        pos = s.get("CarIdxPosition") or 0
        if pos > 0:
            cs.place = pos
            cs.class_place = s.get("CarIdxClassPosition") or cs.class_place
        laps = s.get("CarIdxLapCompleted")
        if laps is not None and laps > cs.laps:
            cs.laps = laps
        best = s.get("CarIdxBestLapTime")
        if best and best > 0:
            cs.best = best
        # Rundenzeit: nach jedem Rundenwechsel die neue „letzte Runde“ abwarten (kommt oft
        # etwas später); ändert sie sich nicht (gleiche Zeit wie davor), nach 5 s übernehmen.
        last = s.get("CarIdxLastLapTime")
        if laps is not None and cs._lap_seen is not None and laps == cs._lap_seen + 1:
            cs._pending_since = st["t"]
            cs._pending_prev = cs._last_lap_time
        elif laps is not None and cs._lap_seen is not None and laps != cs._lap_seen:
            cs._pending_since = None  # Sprung (Aufnahmelücke, neue Session): nicht raten
        if laps is not None:
            cs._lap_seen = laps
        waiting = cs._pending_since
        if (
            waiting is not None
            and last
            and last > 0
            and (last != cs._pending_prev or st["t"] - waiting >= 5.0)
        ):
            cs.lap_times.append(last)
            cs._pending_since = None
        cs._last_lap_time = last
        on_pit = bool(s.get("CarIdxOnPitRoad"))
        if cs._on_pit is False and on_pit:
            cs.pit_entries += 1
        cs._on_pit = on_pit


def _update_own(ses: Session, st: dict[str, Any]) -> None:
    i = st["i"]
    idx = i.get("PlayerCarIdx")
    me = st["c"].get(str(idx)) if idx is not None else None
    llt = i.get("LapLastLapTime")
    prev_llt, ses._own_llt = ses._own_llt, llt
    if me is None or not i.get("IsOnTrack"):
        return
    s = me.get("s", {})
    lap = s.get("CarIdxLapCompleted")
    fuel = i.get("FuelLevel")
    on_pit = bool(s.get("CarIdxOnPitRoad"))
    # Die Zeit der letzten Runde kommt manchmal erst kurz nach dem Rundenwechsel an.
    # Ändert sie sich nicht (exakt gleiche Zeit wie davor), nach 5 s übernehmen.
    pending = ses._own_time_pending
    if (
        pending is not None
        and llt
        and llt > 0
        and ses.own_laps
        and (llt != ses._own_pending_prev or st["t"] - pending >= 5.0)
    ):
        ses.own_laps[-1].time = llt
        ses._own_time_pending = None
    if lap is None:
        return
    if ses._own_lap is None:
        ses._own_lap, ses._own_fuel, ses._own_pit = lap, fuel, on_pit
    elif lap != ses._own_lap:
        if lap == ses._own_lap + 1:
            fresh = bool(llt and llt > 0 and llt != prev_llt)
            ses._own_pending_prev = prev_llt
            ses.own_laps.append(
                OwnLap(
                    lap=lap,
                    time=llt if fresh else None,
                    fuel_start=ses._own_fuel,
                    fuel_end=fuel,
                    pit=ses._own_pit or on_pit,
                )
            )
            ses._own_time_pending = None if fresh else st["t"]
        ses._own_lap, ses._own_fuel, ses._own_pit = lap, fuel, on_pit
    elif on_pit:
        ses._own_pit = True


def iracing_files(path: Path) -> list[Path]:
    """Wie ``recording_files``, aber in einem Ordner nur die iRacing-Dateien."""
    files = recording_files(path)
    if Path(path).is_dir():
        files = [f for f in files if f.name.startswith("iRacing_")]
    return files


def analyse(path: Path) -> dict[str, Any]:
    files = iracing_files(path)
    headers: list[dict[str, Any]] = []
    sessions: list[Session] = []
    cur: Session | None = None
    si: dict[str, Any] = {}
    last_time = None
    total = 0

    for fp in files:
        dec = DeltaDecoder()
        for line in read_lines(fp):
            if "typ" in line:
                headers.append(line)
                continue
            if "si" in line:
                si = line["si"]
            st = dec.apply(line)
            if st is None:
                continue
            total += 1
            i = st["i"]
            num = i.get("SessionNum", -1)
            stime = i.get("SessionTime") or 0.0
            track = track_name(si)
            if (
                cur is None
                or num != cur.num
                or track != cur.track
                or (last_time is not None and stime + 1.0 < last_time)
            ):
                cur = Session(num=num, label=session_label(si, num), track=track, first_t=st["t"])
                sessions.append(cur)
            last_time = stime
            cur.last_t = st["t"]
            cur.frames += 1
            _update_cars(cur, st)
            _update_own(cur, st)

    return {
        "files": [str(f) for f in files],
        "headers": headers,
        "frames": total,
        "sessions": sessions,
    }


def standings(ses: Session) -> list[CarStats]:
    cars = [c for c in ses.cars.values() if not c.pace_car and (c.laps > 0 or c.place > 0)]
    big = 10_000
    cars.sort(key=lambda c: (c.place or big, -c.laps, c.best or 1e9))
    return cars


# --- Ausgabe -------------------------------------------------------------------


def fmt_time(t: float | None) -> str:
    if t is None or t <= 0:
        return "–"
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:06.3f}".replace(".", ",")


def fmt_dur(sec: float) -> str:
    sec = max(0, int(sec))
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}"


def report(res: dict[str, Any]) -> str:
    out: list[str] = []
    h = res["headers"][0] if res["headers"] else {}
    out.append(
        f"Aufnahme: {len(res['files'])} Datei(en), {res['frames']} Messpunkte, "
        f"Recorder {h.get('recorder', '?')}, Spiel {h.get('sim', '?')}"
    )
    for ses in res["sessions"]:
        out.append("")
        out.append(
            f"=== {ses.label} – {ses.track} – Dauer {fmt_dur(ses.last_t - ses.first_t)} "
            f"({ses.frames} Messpunkte) ==="
        )
        rows = standings(ses)
        classes = sorted({c.cls for c in rows})
        out.append(f"Endstand ({len(rows)} Autos, Klassen: {', '.join(classes) or '–'}):")
        out.append(
            "  Pos  Kl.  #     Fahrer                     Auto                      Runden  Beste      Box"
        )
        for c in rows:
            mark = " <- du" if c.player else ""
            out.append(
                f"  {c.place or '-':>3}  {c.class_place or '-':>3}  {c.number:<5} {c.name[:26]:<26} "
                f"{(c.car or c.cls)[:25]:<25} {c.laps:>6}  {fmt_time(c.best):<9}  {c.pit_entries:>3}{mark}"
            )
        if ses.own_laps:
            out.append("Deine Runden:")
            for lap in ses.own_laps:
                used = lap.fuel_used
                if used is None:
                    fuel = "–"
                elif used < 0:
                    fuel = "nachgetankt"
                else:
                    fuel = f"{used:.2f} l".replace(".", ",")
                box = "  (Box)" if lap.pit else ""
                out.append(f"  Runde {lap.lap:>3}: {fmt_time(lap.time):<9}  Sprit {fuel}{box}")
    return "\n".join(out)


def to_json(res: dict[str, Any]) -> dict[str, Any]:
    def car(c: CarStats) -> dict[str, Any]:
        return {k: v for k, v in asdict(c).items() if not k.startswith("_")}

    return {
        "files": res["files"],
        "headers": res["headers"],
        "frames": res["frames"],
        "sessions": [
            {
                "num": s.num,
                "label": s.label,
                "track": s.track,
                "duration_s": round(s.last_t - s.first_t, 1),
                "frames": s.frames,
                "standings": [car(c) for c in standings(s)],
                "own_laps": [{**asdict(lap), "fuel_used": lap.fuel_used} for lap in s.own_laps],
            }
            for s in res["sessions"]
        ],
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="Boxenfunk-iRacing-Recorder pruefen")
    p.add_argument("pfad", type=Path, help="Aufnahmedatei (.jsonl.gz) oder Ordner")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = p.parse_args(argv)

    files = iracing_files(args.pfad)
    first = next(iter(read_lines(files[0])), {}) if files else {}
    if not files and args.pfad.is_dir():
        files = recording_files(args.pfad)
        first = next(iter(read_lines(files[0])), {}) if files else {}
    if first.get("sim") == "LMU":  # LMU-Aufnahme: an die LMU-Auswertung weitergeben
        from boxenfunk.recorder.analyse import main as lmu_main

        return lmu_main(argv)
    if not files:
        print(f"Keine Aufnahmedateien gefunden in: {args.pfad}")
        return 1

    res = analyse(args.pfad)
    if args.json:
        print(json.dumps(to_json(res), ensure_ascii=False, indent=1))
    else:
        print(report(res))
    return 0
