"""Auswertung einer Aufnahme: Sessions, Endstand (Standings), eigene Runden mit VE/Sprit, Boxenstopps.

Dient zur Datenprüfung (Akzeptanz T1): Lassen sich aus der Aufnahme Standings rekonstruieren?
In welcher Einheit kommt die Virtual Energy? Bekommen wir VE/Sprit der Gegner?
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from boxenfunk.recorder.delta import DeltaDecoder
from boxenfunk.recorder.files import read_lines, recording_files


def session_label(code: int) -> str:
    from boxenfunk.recorder.recorder import session_name

    return session_name(code)


@dataclass
class Lap:
    lap: int
    time: float | None
    ve_start: float | None
    ve_end: float | None
    fuel_start: float | None
    fuel_end: float | None
    pit: bool

    @property
    def invalid(self) -> bool:
        """LMU meldet für ungültige Runden (Track Limits o. Ä.) keine Rundenzeit (mLastLapTime = -1)."""
        return not self.pit and (self.time is None or self.time <= 0)

    @property
    def ve_used(self) -> float | None:
        if self.ve_start is None or self.ve_end is None:
            return None
        return self.ve_start - self.ve_end

    @property
    def fuel_used(self) -> float | None:
        if self.fuel_start is None or self.fuel_end is None:
            return None
        return self.fuel_start - self.fuel_end


@dataclass
class Stop:
    lap: int
    t_in: float
    t_out: float | None = None
    ve_in: float | None = None
    ve_out: float | None = None
    fuel_in: float | None = None
    fuel_out: float | None = None


@dataclass
class Session:
    code: int
    track: str
    first_t: float
    last_t: float = 0.0
    frames: int = 0
    final: dict[str, Any] = field(default_factory=dict)
    laps: list[Lap] = field(default_factory=list)
    stops: list[Stop] = field(default_factory=list)
    ve_values: list[float] = field(default_factory=list)
    opp_ve_cars: set[str] = field(default_factory=set)
    opp_fuel_cars: set[str] = field(default_factory=set)
    # interne Merker
    _lap_no: int | None = None
    _lap_ve: float | None = None
    _lap_fuel: float | None = None
    _lap_pit: bool = False
    _in_pits: bool = False


def standings(cars: dict[str, Any]) -> list[dict[str, Any]]:
    """Wertung aus einem Momentzustand: nach mPlace, dazu Platz in der Klasse."""
    rows = []
    for cid, c in cars.items():
        s = c.get("s", {})
        if not s.get("mPlace"):
            continue
        rows.append(
            {
                "id": cid,
                "place": s["mPlace"],
                "class": s.get("mVehicleClass", ""),
                "driver": s.get("mDriverName", ""),
                "vehicle": s.get("mVehicleName", ""),
                "laps": s.get("mTotalLaps"),
                "best": s.get("mBestLapTime"),
                "last": s.get("mLastLapTime"),
                "pitstops": s.get("mNumPitstops"),
                "behind_leader": s.get("mTimeBehindLeader"),
                "laps_behind": s.get("mLapsBehindLeader"),
                "player": bool(s.get("mIsPlayer")),
                "ve": c.get("v", {}).get("mVirtualEnergy"),
                "fuel_fraction": s.get("mFuelFraction"),
            }
        )
    rows.sort(key=lambda r: r["place"])
    per_class: dict[str, int] = {}
    for r in rows:
        per_class[r["class"]] = per_class.get(r["class"], 0) + 1
        r["class_place"] = per_class[r["class"]]
    return rows


def analyse(path: Path) -> dict[str, Any]:
    files = recording_files(path)
    headers: list[dict[str, Any]] = []
    sessions: list[Session] = []
    cur: Session | None = None
    last_et = None
    total_frames = 0

    for fp in files:
        dec = DeltaDecoder()
        for line in read_lines(fp):
            if "typ" in line:
                headers.append(line)
                continue
            st = dec.apply(line)
            if st is None:
                continue
            total_frames += 1
            info = st["i"]
            code = info.get("mSession", -1)
            et = info.get("mCurrentET", 0.0) or 0.0
            new_session = (
                cur is None
                or code != cur.code
                or (last_et is not None and et + 1.0 < last_et)
                or info.get("mTrackName", "") != cur.track
            )
            if new_session:
                cur = Session(code=code, track=info.get("mTrackName", ""), first_t=st["t"])
                sessions.append(cur)
            last_et = et
            cur.last_t = st["t"]
            cur.frames += 1
            _track_player(cur, st)
            if st["c"]:
                cur.final = {cid: {k: dict(v) for k, v in c.items()} for cid, c in st["c"].items()}

    return {
        "files": [str(f) for f in files],
        "headers": headers,
        "frames": total_frames,
        "sessions": sessions,
    }


def _track_player(ses: Session, st: dict[str, Any]) -> None:
    me = None
    for cid, c in st["c"].items():
        s = c.get("s", {})
        v = c.get("v", {})
        if s.get("mIsPlayer"):
            me = c
        else:
            if v.get("mVirtualEnergy"):
                ses.opp_ve_cars.add(cid)
            if v.get("mFuel") or s.get("mFuelFraction"):
                ses.opp_fuel_cars.add(cid)
    if me is None:
        return
    s, v = me["s"], me.get("v", {})
    ve, fuel = v.get("mVirtualEnergy"), v.get("mFuel")
    if ve is not None:
        ses.ve_values.append(ve)
    laps = s.get("mTotalLaps")
    in_pits = bool(s.get("mInPits"))

    # Rundenwechsel
    if ses._lap_no is None:
        ses._lap_no, ses._lap_ve, ses._lap_fuel, ses._lap_pit = laps, ve, fuel, in_pits
    elif laps is not None and laps != ses._lap_no:
        if laps == ses._lap_no + 1:
            ses.laps.append(
                Lap(
                    lap=laps,
                    time=s.get("mLastLapTime"),
                    ve_start=ses._lap_ve,
                    ve_end=ve,
                    fuel_start=ses._lap_fuel,
                    fuel_end=fuel,
                    pit=ses._lap_pit or in_pits,
                )
            )
        ses._lap_no, ses._lap_ve, ses._lap_fuel, ses._lap_pit = laps, ve, fuel, in_pits
    elif in_pits:
        ses._lap_pit = True

    # Boxenstopps
    if in_pits and not ses._in_pits:
        ses.stops.append(Stop(lap=laps or 0, t_in=st["t"], ve_in=ve, fuel_in=fuel))
    elif not in_pits and ses._in_pits and ses.stops:
        stop = ses.stops[-1]
        stop.t_out, stop.ve_out, stop.fuel_out = st["t"], ve, fuel
    ses._in_pits = in_pits


# --- Ausgabe -------------------------------------------------------------------


def _fmt_time(sec: float | None) -> str:
    if sec is None or sec <= 0:
        return "-"
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:06.3f}"


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{x * 100:.1f} %"


def report(result: dict[str, Any], max_rows: int = 60) -> str:
    out: list[str] = []
    w = out.append
    w(f"Dateien: {len(result['files'])}, Messpunkte: {result['frames']}")
    if result["headers"]:
        h = result["headers"][0]
        w(
            f"Recorder {h.get('recorder')}, Spielversion {h.get('gameVersion')}, Start {h.get('start')}"
        )
    for n, ses in enumerate(result["sessions"], 1):
        dur = (ses.last_t - ses.first_t) / 60
        w("")
        w(f"=== Session {n}: {session_label(ses.code)} auf {ses.track or '?'} ({dur:.0f} min) ===")
        rows = standings(ses.final)
        classes: dict[str, int] = {}
        for r in rows:
            classes[r["class"]] = classes.get(r["class"], 0) + 1
        w("Klassen: " + ", ".join(f"{k} ({v})" for k, v in classes.items()))
        w("Endstand (letzter Messpunkt):")
        w(
            f"{'Pos':>3} {'Kl':>3} {'Klasse':<10} {'Fahrer':<22} {'Rd':>4} {'Beste':>9} {'Stopps':>6} {'VE':>7}"
        )
        for r in rows[:max_rows]:
            mark = " <- du" if r["player"] else ""
            w(
                f"{r['place']:>3} {r['class_place']:>3} {r['class'][:10]:<10} {r['driver'][:22]:<22} "
                f"{r['laps'] if r['laps'] is not None else '-':>4} {_fmt_time(r['best']):>9} "
                f"{r['pitstops'] if r['pitstops'] is not None else '-':>6} {_pct(r['ve']):>7}{mark}"
            )
        if ses.ve_values:
            lo, hi = min(ses.ve_values), max(ses.ve_values)
            unit = (
                "Anteil 0 bis 1 (1 = 100 %)"
                if hi <= 1.0001
                else "Prozent oder andere Einheit (prüfen!)"
            )
            w(f"Eigene VE: min {lo:.4f}, max {hi:.4f} -> Einheit vermutlich: {unit}")
        w(f"Gegner mit VE-Wert: {len(ses.opp_ve_cars)}, mit Sprit-Wert: {len(ses.opp_fuel_cars)}")
        if ses.laps:
            w("Eigene Runden:")
            w(f"{'Rd':>4} {'Zeit':>9} {'VE-Verbrauch':>12} {'Sprit (l)':>9} Box")
            for lap in ses.laps:
                vu = "-" if lap.ve_used is None else f"{lap.ve_used * 100:.2f} %"
                fu = "-" if lap.fuel_used is None else f"{lap.fuel_used:.2f}"
                w(
                    f"{lap.lap:>4} {_fmt_time(lap.time):>9} {vu:>12} {fu:>9} {'ja' if lap.pit else ''}"
                    f"{'ungültig' if lap.invalid else ''}"
                )
        if ses.stops:
            w("Eigene Boxenstopps:")
            for s in ses.stops:
                dt = "-" if s.t_out is None else f"{s.t_out - s.t_in:.1f} s"
                w(f"  Runde {s.lap}: Boxengasse {dt}, VE {_pct(s.ve_in)} -> {_pct(s.ve_out)}")
    return "\n".join(out)


def to_json(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "files": result["files"],
        "frames": result["frames"],
        "headers": result["headers"],
        "sessions": [
            {
                "session": ses.code,
                "track": ses.track,
                "minutes": round((ses.last_t - ses.first_t) / 60, 1),
                "standings": standings(ses.final),
                "laps": [{**lap.__dict__, "invalid": lap.invalid} for lap in ses.laps],
                "stops": [s.__dict__ for s in ses.stops],
                "ve_min": min(ses.ve_values) if ses.ve_values else None,
                "ve_max": max(ses.ve_values) if ses.ve_values else None,
                "opp_ve_cars": len(ses.opp_ve_cars),
                "opp_fuel_cars": len(ses.opp_fuel_cars),
            }
            for ses in result["sessions"]
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="Boxenfunk-Recorder pruefen")
    p.add_argument("pfad", type=Path, help="Aufnahmedatei (.jsonl.gz) oder Ordner")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON ausgeben")
    args = p.parse_args(argv)
    result = analyse(args.pfad)
    if args.json:
        print(json.dumps(to_json(result), indent=1, ensure_ascii=False))
    else:
        print(report(result))
    return 0
