from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
from fake_iracing import FakeIRacing

from boxenfunk.adapters.iracing.sdk import IRacingSource, anonymize_raw
from boxenfunk.recorder import iracing_analyse, iracing_recorder, iracing_snapshot
from boxenfunk.recorder.delta import DeltaDecoder
from boxenfunk.recorder.files import read_lines, read_raw


class FakeClock:
    def __init__(self, t: float = 1_700_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def make(tmp_path: Path, **kw):
    sim = FakeIRacing()
    clock = FakeClock()
    logs: list[str] = []
    src = IRacingSource(ir=sim.ir, clock=clock)
    rec = iracing_recorder.IRacingRecorder(src, tmp_path, clock=clock, log=logs.append, **kw)
    return sim, rec, clock, logs


def drive(sim: FakeIRacing, rec, clock: FakeClock, seconds: float, hz: float = 5) -> None:
    dt = 1.0 / hz
    for _ in range(int(seconds * hz)):
        sim.tick(dt)
        clock.t += dt
        rec.step()


# --- Momentaufnahme -------------------------------------------------------------


def test_snapshot_has_all_cars_with_class_and_no_private_data():
    sim = FakeIRacing()
    sim.tick(30)
    src = IRacingSource(ir=sim.ir)
    assert src.update()
    snap = iracing_snapshot.snapshot(src)
    assert len(snap["c"]) == 8  # 7 Autos + Pace-Car
    me = snap["c"]["5"]
    assert me["v"]["UserName"] == "Robert Test"
    assert me["v"]["CarClassShortName"] == "GT3"
    assert "UserID" not in me["v"]
    assert me["s"]["CarIdxPosition"] >= 1
    assert "CarIdxRPM" not in me["s"]  # unnötig, wechselt ständig
    assert "LatAccel" not in snap["i"] and "LatAccel_ST" not in snap["tel"]
    assert snap["tel"]["TestTireTemps"] == [80.0, 81.0, 82.0]
    assert 0 < snap["i"]["FuelLevel"] <= 60.0
    rest = iracing_snapshot.session_rest(src.session_info())
    assert "Drivers" not in rest["DriverInfo"]
    assert "DriverUserID" not in rest["DriverInfo"]
    assert "ResultsPositions" not in rest["SessionInfo"]["Sessions"][0]


def test_results_are_attached_per_car():
    sim = FakeIRacing()
    sim.tick(250)
    src = IRacingSource(ir=sim.ir)
    src.update()
    snap = iracing_snapshot.snapshot(src)
    leader = next(c for c in snap["c"].values() if c["s"].get("CarIdxPosition") == 1)
    assert leader["v"]["res"]["Position"] == 1


def test_real_pyirsdk_reads_memory_dump(tmp_path):
    """Echter Lesepfad über pyirsdk (Testmodus mit Speicherabbild statt laufendem iRacing)."""
    sim = FakeIRacing()
    sim.tick(250)
    dump = sim.dump(tmp_path / "ir.bin")
    src = IRacingSource(test_file=str(dump))
    try:
        assert src.update()
        snap = iracing_snapshot.snapshot(src)
        assert snap["i"]["SessionTime"] == pytest.approx(250.0)
        assert snap["i"]["PlayerCarIdx"] == 5
        me = snap["c"]["5"]
        assert me["v"]["UserName"] == "Robert Test"
        assert me["s"]["CarIdxLapCompleted"] == sim.values()["CarIdxLapCompleted"][5]
        assert me["s"]["CarIdxOnPitRoad"] in (0, 1)
        assert snap["c"]["0"]["v"]["CarIsPaceCar"] == 1
        raw = src.raw()
        assert raw is not None and b"UserID: 123461" not in raw and b"UserID: 000000" in raw
    finally:
        src.close()


def test_anonymize_raw_keeps_length():
    blob = b"DriverUserID: 98765\n UserID: 12\n"
    out = anonymize_raw(blob)
    assert len(out) == len(blob) and b"98765" not in out and b"12\n" not in out


# --- Recorder -------------------------------------------------------------------


def test_recording_roundtrip_and_session_info(tmp_path):
    sim, rec, clock, logs = make(tmp_path)
    drive(sim, rec, clock, 60)
    rec.close()
    files = sorted(tmp_path.glob("iRacing_*.jsonl.gz"))
    assert len(files) == 1
    lines = list(read_lines(files[0]))
    assert lines[0]["sim"] == "iRacing" and lines[0]["gameVersion"] == "2026.11.10.01"
    assert "si" in lines[1] and lines[1].get("k") == 1
    assert lines[1]["si"]["WeekendInfo"]["TrackDisplayName"].startswith("Circuit de Spa")
    dec = DeltaDecoder()
    st = None
    for line in lines[1:]:
        st = dec.apply(line)
    assert st["i"]["SessionTime"] == pytest.approx(60.0, abs=0.3)
    assert st["c"]["5"]["v"]["UserName"] == "Robert Test"
    assert any("Verbunden" in m for m in logs)
    assert any("Strecke: Circuit de Spa" in m and "Du: P" in m for m in logs)
    # Rohkopie vorhanden und anonymisiert
    raws = list(read_raw(next(tmp_path.glob("iRacing_*.roh.gz"))))
    assert raws and b"123456" not in raws[0][1]


def test_waits_without_game_and_reconnects(tmp_path):
    sim, rec, clock, logs = make(tmp_path)
    sim.ir.running = False
    drive(sim, rec, clock, 10)
    assert rec.frames == 0
    assert any("Warte auf iRacing" in m for m in logs)
    assert not list(tmp_path.glob("*.jsonl.gz"))
    # nur alle 2 s ein Verbindungsversuch
    assert sim.ir.startups <= 6
    sim.ir.running = True
    drive(sim, rec, clock, 5)
    assert rec.frames > 0
    # Spiel beendet -> Warten, danach wieder verbunden
    sim.ir.running = False
    drive(sim, rec, clock, 5)
    assert any("Keine neuen Daten" in m for m in logs)
    sim.ir.running = True
    drive(sim, rec, clock, 5)
    assert sum("Verbunden" in m for m in logs) == 2


def test_rotation_new_file_starts_with_keyframe_and_session_info(tmp_path):
    sim, rec, clock, _ = make(tmp_path, rotate_s=30)
    drive(sim, rec, clock, 70)
    rec.close()
    files = sorted(tmp_path.glob("iRacing_*.jsonl.gz"))
    assert len(files) == 3
    for f in files:
        lines = list(read_lines(f))
        assert lines[1].get("k") == 1 and "si" in lines[1]


def test_truncated_file_still_readable(tmp_path):
    sim, rec, clock, _ = make(tmp_path)
    drive(sim, rec, clock, 30)
    rec.writer.flush()
    path = rec.writer.path
    data = path.read_bytes()
    cut = tmp_path / "cut" / "iRacing_x_teil01.jsonl.gz"
    cut.parent.mkdir()
    cut.write_bytes(data[: len(data) - 50])
    assert len(list(read_lines(cut))) > 10


# --- Auswertung -----------------------------------------------------------------


def test_analyse_standings_laps_and_pitstop(tmp_path):
    sim, rec, clock, _ = make(tmp_path)
    drive(sim, rec, clock, 700)  # gut 6 Runden
    rec.close()
    res = iracing_analyse.analyse(tmp_path)
    assert len(res["sessions"]) == 1
    ses = res["sessions"][0]
    assert ses.label == "Rennen"
    rows = iracing_analyse.standings(ses)
    assert len(rows) == 7  # ohne Pace-Car
    assert [r.place for r in rows] == list(range(1, 8))
    assert rows[0].cls == "LMP2"
    gt3 = [r for r in rows if r.cls == "GT3"]
    assert [r.class_place for r in gt3] == [1, 2, 3, 4]
    me = next(r for r in rows if r.player)
    assert me.pit_entries == 1
    assert me.lap_times and me.best == pytest.approx(min(me.lap_times))
    other = next(r for r in rows if not r.player and r.cls == "LMP2")
    assert len(other.lap_times) >= 5
    assert other.pit_entries == 0
    # eigene Runden mit Spritverbrauch und Boxenstopp-Markierung
    laps = ses.own_laps
    assert len(laps) >= 4
    assert laps[0].fuel_used == pytest.approx(2.5, abs=0.01)
    assert laps[0].time == pytest.approx(sim.cars[4]["lap_time"], abs=0.01)
    assert any(lap.pit for lap in laps)
    # Rundenzeiten sind in der Simulation immer exakt gleich: trotzdem jede Runde mit Zeit
    assert all(lap.time == pytest.approx(sim.cars[4]["lap_time"], abs=0.01) for lap in laps)
    text = iracing_analyse.report(res)
    assert "Robert Test" in text and "<- du" in text and "Deine Runden" in text
    js = iracing_analyse.to_json(res)
    json.dumps(js)
    assert js["sessions"][0]["standings"][0]["place"] == 1


def test_analyse_ignores_lmu_files_in_folder(tmp_path):
    sim, rec, clock, _ = make(tmp_path)
    drive(sim, rec, clock, 20)
    rec.close()
    with gzip.open(tmp_path / "LMU_2026-01-01_00-00-00_teil01.jsonl.gz", "wt") as f:
        f.write(json.dumps({"typ": "boxenfunk-aufnahme", "sim": "LMU"}) + "\n")
    res = iracing_analyse.analyse(tmp_path)
    assert all(Path(f).name.startswith("iRacing_") for f in res["files"])


def test_main_pruefen_and_dauer(tmp_path, capsys):
    sim, rec, clock, _ = make(tmp_path / "a")
    drive(sim, rec, clock, 20)
    rec.close()
    assert iracing_recorder.main(["pruefen", str(tmp_path / "a")]) == 0
    assert "Endstand" in capsys.readouterr().out
    # Recorder ohne laufendes Spiel: läuft 1 s, beendet sich sauber, schreibt nichts
    out = tmp_path / "b"
    assert iracing_recorder.main(["--dauer", "1", "--ohne-pause", "--ordner", str(out)]) == 0
    assert "Aufnahme beendet" in capsys.readouterr().out
    assert not list(out.glob("*.jsonl.gz"))


def test_main_with_test_dump_records(tmp_path, capsys):
    sim = FakeIRacing()
    sim.tick(100)
    dump = sim.dump(tmp_path / "ir.bin")
    out = tmp_path / "rec"
    rc = iracing_recorder.main(
        ["--dauer", "1", "--ohne-pause", "--ordner", str(out), "--testdatei", str(dump)]
    )
    assert rc == 0
    files = list(out.glob("iRacing_*.jsonl.gz"))
    assert files
    lines = list(read_lines(files[0]))
    assert lines[1]["c"]["5"]["v"]["UserName"] == "Robert Test"
