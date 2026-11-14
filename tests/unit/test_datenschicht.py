"""Datenschicht des Prototyps: LMU → RaceState, Verlauf (Tracker), Anzeige-Aufbereitung, Wiedergabe."""

from __future__ import annotations

from pathlib import Path

from fake_lmu import TRACK_LEN, FakeLmu

from boxenfunk.adapters.lmu.translate import brand_of, team_and_number, to_race_state
from boxenfunk.adapters.sources import ReplaySource
from boxenfunk.core.tracker import SessionTracker
from boxenfunk.core.views import energy_view, gap_between, standings_blocks
from boxenfunk.model.race_state import CarState, Phase, RaceState, SessionKind
from boxenfunk.recorder import recorder
from boxenfunk.recorder.snapshot import snapshot


def state_of(fake: FakeLmu, t: float = 0.0) -> RaceState:
    snap = snapshot(fake.data)
    snap["t"] = t
    return to_race_state(snap)


def run(fake: FakeLmu, tr: SessionTracker, seconds: float, hz: float = 5) -> RaceState:
    st = None
    for k in range(int(seconds * hz)):
        fake.tick(1 / hz)
        st = state_of(fake, k / hz)
        tr.update(st)
    return st


def test_names_brands_numbers():
    assert team_and_number("Iron Lynx 2026 #79:WEC") == ("Iron Lynx", "79")
    assert team_and_number("911GT3R Custom Team 2026 #397") == ("911GT3R Custom Team", "397")
    assert team_and_number("ohne Nummer") == ("ohne Nummer", "")
    assert brand_of("Porsche 911 GT3 R LMGT3") == "porsche"
    assert brand_of("Mercedes-AMG LMGT3") == "mercedes"
    assert brand_of("Aston Martin Vantage AMR LMGT3") == "astonmartin"
    assert brand_of("") == ""


def test_translate_positions_classes_and_player():
    fake = FakeLmu()
    fake.tick(0.2)
    st = state_of(fake)
    assert st.sim == "LMU" and st.session_kind == SessionKind.RENNEN and st.session_no == 1
    assert st.phase == Phase.GRUEN
    assert st.track_length == TRACK_LEN
    assert [c.position for c in st.cars] == list(range(1, len(fake.cars) + 1))
    assert st.classes() == ["Hyper", "GT3"]
    me = st.player_car()
    assert me is not None and me.is_player and st.player is not None
    assert me.car_class == "GT3" and me.class_position == 2
    assert 0 < st.player.energy <= 1


def test_tracker_counts_laps_usage_and_relative():
    fake = FakeLmu()
    tr = SessionTracker()
    st = run(fake, tr, seconds=4 * 125)
    me = st.player_car()
    assert me.laps >= 3
    assert len(tr.recent_laps(me.car_id)) == 3
    avg = tr.usage_average("energy")
    assert avg is not None and abs(avg - 0.07) < 0.005  # Fake verbraucht 7 % pro Runde
    rel = tr.relative(st)
    assert any(e.car.is_player and e.gap == 0 for e in rel)
    gaps = [e.gap for e in rel]
    assert gaps == sorted(gaps)

    ev = energy_view(st, tr, "energy")
    assert ev is not None and ev.laps_left is not None
    assert ev.target_laps == int(ev.laps_left) + 1
    assert abs(ev.allowed_per_lap * ev.target_laps - ev.level) < 1e-9


def test_standings_blocks_show_top_and_me():
    fake = FakeLmu(n_hyper=3, n_gt3=12, player_index=12)
    tr = SessionTracker()
    st = run(fake, tr, seconds=130)
    blocks = dict(standings_blocks(st, tr, top=3, around=2, other_top=2))
    assert len(blocks["Hyper"]) == 2
    gt3 = blocks["GT3"]
    assert any(r.car.is_player for r in gt3)
    assert [r.car.class_position for r in gt3][:3] == [1, 2, 3]
    assert any(r.gap_before for r in gt3)  # Lücke zwischen Spitze und „um mich“
    assert gt3[0].gap == "" and gt3[1].gap != ""


def _car(pos: int, laps: int, dist: float, gap_ahead: float) -> CarState:
    return CarState(
        car_id=str(pos),
        driver="x",
        number="1",
        team="",
        model="",
        brand="",
        car_class="GT3",
        position=pos,
        laps=laps,
        lap_dist=dist,
        gap_ahead=gap_ahead,
    )


def test_gap_between_sums_intervals_and_counts_laps():
    cars = [
        _car(1, 10, 3000, 0),
        _car(2, 10, 2900, 1.5),
        _car(3, 10, 2800, 2.0),
        _car(4, 9, 2000, 50),
    ]
    st = RaceState(
        sim="LMU",
        wall_time=0,
        session_kind=SessionKind.RENNEN,
        session_no=1,
        session_time=0,
        session_end=None,
        max_laps=None,
        phase=Phase.GRUEN,
        track="T",
        track_length=5000,
        cars=cars,
    )
    assert gap_between(st, cars[2], cars[0]) == "3.5"
    assert gap_between(st, cars[3], cars[0]) == "+1L"


def test_replay_source_plays_recording(tmp_path: Path):
    fake = FakeLmu()
    t = [1_700_000_000.0]
    rec = recorder.Recorder(fake, tmp_path, clock=lambda: t[0], log=lambda m: None)
    for _ in range(5 * 60):
        fake.tick(0.2)
        t[0] += 0.2
        rec.step()
    rec.close()
    frames = list(ReplaySource(tmp_path).frames())
    assert len(frames) > 250
    assert frames[-1].session_time > frames[0].session_time
    assert all(f.player_car() is not None for f in frames)

    src = ReplaySource(tmp_path, speed=1000.0)
    first = src.poll()
    assert first is not None


def test_relative_measured_gap_follows_track_time(tmp_path: Path):
    """Gemessener Abstand: Auto 1,5 s vor mir mit gleichem Tempo → Relative zeigt −1,5 s."""
    fake = FakeLmu(n_hyper=0, n_gt3=2, player_index=1)
    for c in fake.cars:
        c["lap_time"] = 120.0
        c["ve_per_lap"] = 0.0
    fake.cars[0]["dist"] = fake.cars[1]["dist"] + TRACK_LEN * 1.5 / 120.0
    tr = SessionTracker()
    st = run(fake, tr, seconds=30)
    rel = tr.relative(st)
    ahead = next(e for e in rel if not e.car.is_player)
    assert abs(ahead.gap + 1.5) < 0.05


def test_trend_grows_from_left():
    fake = FakeLmu(n_hyper=0, n_gt3=3, player_index=1)
    tr = SessionTracker()
    st = run(fake, tr, seconds=130)
    other = next(c for c in st.cars if not c.is_player)
    assert 1 <= len(tr.trend(st, other)) <= 3


def test_abgleich_runs(tmp_path: Path, capsys):
    from boxenfunk.core import abgleich

    fake = FakeLmu()
    t = [1_700_000_000.0]
    rec = recorder.Recorder(fake, tmp_path, clock=lambda: t[0], log=lambda m: None)
    for _ in range(5 * 30):
        fake.tick(0.2)
        t[0] += 0.2
        rec.step()
    rec.close()
    assert abgleich.main([str(tmp_path)]) == 0
    assert "Relative" in capsys.readouterr().out


def test_pitstate_5_on_track_is_not_garage():
    """LMU meldet mPitState 5 auch für Autos auf der Strecke (Roberts Test 14.11.)."""
    snap = {
        "i": {"mSession": 1, "mLapDist": 5000.0, "mGamePhase": 5, "mCurrentET": 100.0},
        "c": {
            "1": {"s": {"mPlace": 1, "mIsPlayer": 1, "mLapDist": 1000.0, "mVehicleClass": "GT3"}},
            "2": {"s": {"mPlace": 2, "mPitState": 5, "mLapDist": 1400.0, "mVehicleClass": "GT3"}},
            "3": {
                "s": {
                    "mPlace": 3,
                    "mPitState": 5,
                    "mInPits": 1,
                    "mInGarageStall": 1,
                    "mLapDist": 50.0,
                    "mVehicleClass": "GT3",
                }
            },
        },
    }
    st = to_race_state(snap)
    car2 = next(c for c in st.cars if c.car_id == "2")
    assert not car2.in_garage and car2.pit_state.value == ""
    rel = SessionTracker().relative(st)
    ids = [e.car.car_id for e in rel]
    assert "2" in ids and "3" not in ids


def test_standings_only_my_class_and_practice_gaps():
    fake = FakeLmu(n_hyper=3, n_gt3=6, player_index=5)
    tr = SessionTracker()
    st = run(fake, tr, seconds=300)
    blocks = standings_blocks(st, tr, only_my_class=True)
    assert [cls for cls, _ in blocks] == ["GT3"]
    # Im Training zählt der Rückstand der Bestzeit, nicht die Runden
    st.session_kind = SessionKind.TRAINING
    rows = dict(standings_blocks(st, tr))["GT3"]
    assert all("L" not in r.gap and "L" not in r.interval for r in rows)
