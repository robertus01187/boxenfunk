from __future__ import annotations

import gzip
import json
import shutil
import uuid
from pathlib import Path

import pytest
from fake_lmu import FakeLmu

from boxenfunk.adapters.lmu import lmu_data as d
from boxenfunk.adapters.lmu import shm
from boxenfunk.recorder import analyse, recorder, snapshot
from boxenfunk.recorder.delta import DeltaDecoder, DeltaEncoder
from boxenfunk.recorder.files import read_lines, read_raw, recording_files


class FakeClock:
    def __init__(self, t: float = 1_700_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def drive(fake: FakeLmu, rec: recorder.Recorder, clock: FakeClock, seconds: float, hz: float = 5):
    dt = 1.0 / hz
    for _ in range(int(seconds * hz)):
        fake.tick(dt)
        clock.t += dt
        rec.step()


# --- Momentaufnahme -------------------------------------------------------------


def test_snapshot_matches_telemetry_by_slot_id():
    fake = FakeLmu()
    fake.tick(30)
    snap = snapshot.snapshot(fake.data)
    assert len(snap["c"]) == 7
    for c in fake.cars:
        car = snap["c"][str(c["id"])]
        assert car["s"]["mVehicleClass"] == c["cls"]
        assert car["v"]["mVirtualEnergy"] == pytest.approx(c["ve"], abs=1e-5)


def test_snapshot_player_has_details_opponents_slim_and_no_personal_data():
    fake = FakeLmu(player_index=4)
    snap = snapshot.snapshot(fake.data)
    player = snap["c"]["14"]
    other = snap["c"]["10"]
    assert player["s"]["mIsPlayer"] == 1
    assert "mEngineRPM" in player["v"]
    assert "mTemperature" in player["v"]["mWheels"][0]
    assert "mEngineRPM" not in other["v"]
    assert other["v"]["mWheels"][0]["mWear"] == pytest.approx(0.97, abs=1e-6)
    assert "mSteamID" not in other["s"]
    assert "mServerPublicIP" not in snap["i"]
    assert snap["i"]["mTrackName"] == "Bahrain International Circuit"
    json.dumps(snap)  # muss JSON-tauglich sein


def test_nan_becomes_null():
    assert snapshot.num(float("nan")) is None
    assert snapshot.num(0.123456789) == 0.123457
    assert snapshot.num(1234.56789) == 1234.568


def test_anonymized_raw_removes_paths_and_steam_ids():
    fake = FakeLmu()
    raw = snapshot.anonymized_raw(fake.data)
    assert len(raw) == shm.SIZE
    back = d.LMUObjectOut.from_buffer_copy(raw)
    assert back.paths.userData == b""
    assert all(v.mSteamID == 0 for v in back.scoring.vehScoringInfo)
    assert back.scoring.vehScoringInfo[0].mID == 10
    assert fake.data.scoring.vehScoringInfo[0].mSteamID != 0  # Original unverändert


# --- Delta-Kodierung --------------------------------------------------------------


def test_delta_roundtrip_including_car_leaving():
    fake = FakeLmu()
    enc, dec = DeltaEncoder(), DeltaDecoder()
    for step in range(40):
        fake.tick(0.2)
        if step == 20:
            fake.cars.pop(1)
            fake.data.scoring.scoringInfo.mNumVehicles = len(fake.cars)
        snap = snapshot.snapshot(fake.data)
        frame = enc.encode(snap, float(step))
        if step == 0:
            assert frame["k"] == 1
        state = dec.apply(json.loads(json.dumps(frame)))
        assert state["c"] == snap["c"]
        assert state["i"] == snap["i"]


def test_delta_unchanged_returns_none_and_is_small():
    fake = FakeLmu()
    enc = DeltaEncoder()
    snap = snapshot.snapshot(fake.data)
    full = enc.encode(snap, 0.0)
    assert enc.encode(snapshot.snapshot(fake.data), 0.2) is None
    fake.tick(0.2)
    small = enc.encode(snapshot.snapshot(fake.data), 0.4)
    assert len(json.dumps(small)) < len(json.dumps(full)) / 4


# --- Recorder ----------------------------------------------------------------------


def test_recorder_full_race_and_analysis(tmp_path: Path):
    fake = FakeLmu()
    clock = FakeClock()
    logs: list[str] = []
    rec = recorder.Recorder(fake, tmp_path, rotate_s=600, raw_s=300, clock=clock, log=logs.append)
    drive(fake, rec, clock, seconds=27 * 60)
    rec.close()

    files = recording_files(tmp_path)
    assert len(files) == 3  # Rotation alle 10 min
    assert len(list(tmp_path.glob("*.roh.gz"))) == 3
    assert fake.cars[4]["stops"] == 1 and not fake.cars[4]["refill"]
    first = next(read_lines(files[0]))
    assert first["typ"] == "boxenfunk-aufnahme" and first["teil"] == 1
    assert any("Verbunden" in m for m in logs)
    assert any("VE " in m and "Du: P" in m for m in logs)

    res = analyse.analyse(tmp_path)
    assert len(res["sessions"]) == 1
    ses = res["sessions"][0]
    rows = analyse.standings(ses.final)
    # Rekonstruierte Wertung = Wertung im (simulierten) Spiel
    expected = sorted(fake.cars, key=lambda c: -(c["laps"] + c["dist"] / 5412.0))
    assert [r["id"] for r in rows] == [str(c["id"]) for c in expected]
    gt3 = [r for r in rows if r["class"] == "GT3"]
    assert [r["class_place"] for r in gt3] == list(range(1, len(gt3) + 1))

    player = fake.cars[4]
    assert len(ses.laps) == player["laps"]
    normal = [lap for lap in ses.laps if not lap.pit]
    assert normal[1].ve_used == pytest.approx(0.07, abs=0.002)
    assert len(ses.stops) == player["stops"] >= 1
    assert ses.stops[0].ve_in < 0.2
    assert ses.stops[0].ve_out == pytest.approx(1.0, abs=0.01)
    assert ses.stops[0].t_out - ses.stops[0].t_in == pytest.approx(30, abs=1)
    assert max(ses.ve_values) <= 1.0
    assert len(ses.opp_ve_cars) == 6

    text = analyse.report(res)
    assert "Rennen 1" in text and "<- du" in text and "Anteil 0 bis 1" in text
    assert analyse.to_json(res)["sessions"][0]["opp_ve_cars"] == 6

    raws = list(read_raw(sorted(tmp_path.glob("*.roh.gz"))[0]))
    assert raws and len(raws[0][1]) == shm.SIZE


def test_recorder_waits_while_game_not_running(tmp_path: Path):
    class Empty:
        data = d.LMUObjectOut()

        def update(self) -> bool:
            return False

    clock = FakeClock()
    logs: list[str] = []
    rec = recorder.Recorder(Empty(), tmp_path / "out", clock=clock, log=logs.append)
    for _ in range(50):
        clock.t += 0.2
        assert rec.step() is False
    rec.close()
    assert not list((tmp_path / "out").glob("*.jsonl.gz"))
    assert any("Warte auf Le Mans Ultimate" in m for m in logs)


def test_recorder_pause_detection(tmp_path: Path):
    fake = FakeLmu()
    clock = FakeClock()
    logs: list[str] = []
    rec = recorder.Recorder(fake, tmp_path, clock=clock, log=logs.append)
    drive(fake, rec, clock, 10)
    for _ in range(30):  # Spiel pausiert: Zeit steht
        clock.t += 0.2
        rec.step()
    assert not rec.alive
    drive(fake, rec, clock, 5)
    assert rec.alive
    rec.close()
    assert sum("Verbunden" in m for m in logs) == 2


def test_truncated_file_is_still_readable(tmp_path: Path):
    fake = FakeLmu()
    clock = FakeClock()
    rec = recorder.Recorder(fake, tmp_path / "rec", clock=clock, log=lambda m: None)
    drive(fake, rec, clock, 120)
    rec.writer.flush()
    src = recording_files(tmp_path / "rec")[0]
    # Simulierter Absturz: Datei wird ohne sauberes Ende abgeschnitten
    broken = tmp_path / "kaputt.jsonl.gz"
    shutil.copy(src, broken)
    data = broken.read_bytes()
    broken.write_bytes(data[: len(data) - 37])
    lines = list(read_lines(broken))
    assert len(lines) > 400
    with pytest.raises((EOFError, gzip.BadGzipFile)), gzip.open(broken) as f:
        f.read()
    rec.close()


# --- Kommandozeile mit echtem Shared-Memory-Zugriff ---------------------------------


def test_main_records_from_shared_memory(tmp_path: Path, capsys):
    name = f"Boxenfunk_Test_{uuid.uuid4().hex[:8]}"
    fake = FakeLmu()
    fake.tick(5)
    mm = shm._open(name, shm.SIZE)
    mm[:] = bytes(fake.data)
    try:
        rc = recorder.main(["--ordner", str(tmp_path), "--dauer", "1.2", "--quelle", name])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Verbunden" in out
        files = recording_files(tmp_path)
        assert len(files) == 1
        lines = list(read_lines(files[0]))
        assert lines[1]["k"] == 1 and len(lines[1]["c"]) == 7

        assert recorder.main(["pruefen", str(tmp_path)]) == 0
        assert "Bahrain" in capsys.readouterr().out
        assert recorder.main([str(files[0])]) == 0  # Drag & Drop auf die exe
    finally:
        mm.close()
        Path(f"/dev/shm/{name}").unlink(missing_ok=True)


def test_shm_skips_inconsistent_then_forces(tmp_path: Path):
    name = f"Boxenfunk_Test_{uuid.uuid4().hex[:8]}"
    fake = FakeLmu()
    fake.data.telemetry.activeVehicles = 3  # passt nicht zu mNumVehicles=7
    mm = shm._open(name, shm.SIZE)
    mm[:] = bytes(fake.data)
    try:
        src = shm.LmuSharedMemory(name)
        results = [src.update() for _ in range(shm.FORCE_AFTER + 1)]
        assert results[: shm.FORCE_AFTER] == [False] * shm.FORCE_AFTER
        assert results[-1] is True and src.forced == 1
        assert src.data.scoring.scoringInfo.mNumVehicles == 7
    finally:
        mm.close()
        Path(f"/dev/shm/{name}").unlink(missing_ok=True)
