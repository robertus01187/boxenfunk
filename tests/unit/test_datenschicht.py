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
    # Wie TinyPedal: Schätzung aus der letzten gültigen Runde, Ziel ab Stand zu Rundenbeginn
    assert ev.est_per_lap is not None and abs(ev.est_per_lap - 0.07) < 0.003
    at_start = ev.level + tr.consumption["energy"].used_curr
    assert ev.target_laps == int(round(at_start / ev.est_per_lap, 1)) + 1
    assert abs(ev.allowed_per_lap * ev.target_laps - at_start) < 1e-9
    assert ev.avg_per_lap is not None


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


def test_relative_uses_game_time_into_lap():
    """Wie LMU selbst (und TinyPedal): Abstand aus mTimeIntoLap, über Start/Ziel hinweg."""
    snap = {
        "i": {"mSession": 10, "mLapDist": 5000.0, "mGamePhase": 5, "mCurrentET": 100.0},
        "c": {
            "1": {
                "s": {
                    "mPlace": 2,
                    "mIsPlayer": 1,
                    "mLapDist": 4900.0,
                    "mTimeIntoLap": 118.0,
                    "mEstimatedLapTime": 120.0,
                    "mVehicleClass": "GT3",
                }
            },
            "2": {
                "s": {
                    "mPlace": 1,
                    "mLapDist": 100.0,
                    "mTimeIntoLap": 1.5,
                    "mEstimatedLapTime": 120.0,
                    "mVehicleClass": "GT3",
                }
            },
            "3": {
                "s": {
                    "mPlace": 3,
                    "mLapDist": 4800.0,
                    "mTimeIntoLap": 115.2,
                    "mEstimatedLapTime": 120.0,
                    "mVehicleClass": "GT3",
                }
            },
        },
    }
    rel = {e.car.car_id: e.gap for e in SessionTracker().relative(to_race_state(snap))}
    assert abs(rel["2"] + 3.5) < 1e-9 and abs(rel["3"] - 2.8) < 1e-9


def _flag_snap(sector=(0, 0, 0), blue=False, slow_dist=None, behind_cls="Hyper", behind_laps=6):
    def car(place, dist, tinto, cls="GT3", laps=5, speed=50.0, **kw):
        s = {
            "mPlace": place,
            "mLapDist": dist,
            "mTimeIntoLap": tinto,
            "mEstimatedLapTime": 120.0,
            "mVehicleClass": cls,
            "mTotalLaps": laps,
            "mLocalVel": {"x": 0.0, "y": 0.0, "z": speed},
        }
        s.update(kw)
        return {"s": s}

    cars = {
        "1": car(2, 1000.0, 24.0, mIsPlayer=1, mFlag=6 if blue else 0),
        "2": car(1, 900.0, 22.6, cls=behind_cls, laps=behind_laps),
    }
    if slow_dist is not None:
        cars["3"] = car(3, 1000.0 + slow_dist, 30.0, speed=2.0)
    return {
        "i": {
            "mSession": 10,
            "mLapDist": 5000.0,
            "mGamePhase": 5,
            "mCurrentET": 100.0,
            "mSectorFlag": list(sector),
        },
        "c": cars,
    }


def test_flags_yellow_distance_like_tinypedal():
    from boxenfunk.core.flags import FlagState

    fs = FlagState()
    assert fs.update(to_race_state(_flag_snap(sector=(1, 0, 0), slow_dist=230)), None)[0].info == (
        "▲ 230 m"
    )
    # Mehr als 500 m vor mir: keine Flagge (wie TinyPedal)
    far = to_race_state(_flag_snap(sector=(1, 0, 0), slow_dist=700))
    assert FlagState().update(far, None) == []
    # Gelb vorbei → kurz Grün
    flags = FlagState()
    flags.update(to_race_state(_flag_snap(sector=(1, 0, 0), slow_dist=100)), None)
    assert [f.kind for f in flags.update(to_race_state(_flag_snap()), None)] == ["gruen"]


def test_flags_blue_shows_class_of_lapping_car():
    from boxenfunk.core.flags import FlagState, class_label

    f = FlagState().update(to_race_state(_flag_snap(blue=True)), None)
    assert f[0].kind == "blau" and f[0].info.startswith("HYPERCAR") and "1.4 s" in f[0].info
    assert class_label("LMP2 ELMS") == "LMP2" and class_label("LMGT3") == "GT3"


def test_consumption_reacts_within_lap_like_tinypedal():
    """Wer in der laufenden Runde spart, sieht es sofort an der Schätzung."""
    from boxenfunk.core.consumption import Consumption

    c = Consumption()
    t = 0.0
    level = 1.0
    for lap in range(0, 3):
        for k in range(1, 101):  # 100 Schritte à 50 m, 5000 m Runde, 5 % pro Runde
            t += 1
            dist = k * 50.0 if k < 100 else 10.0
            level -= 0.0005
            c.update(level, lap + (k == 100), dist, t, 50, False, False, True)
        t += 1
        c.update(level, lap + 1, 60.0, t, 50, False, False, True)
    assert c.used_last_valid is not None and abs(c.used_last_valid - 0.05) < 0.002
    # Halbe Runde mit halbem Verbrauch → Schätzung sinkt um ~1,25 %
    for k in range(2, 51):
        t += 1
        level -= 0.00025
        c.update(level, 3, k * 50.0, t, 50, False, False, True)
    assert c.estimate is not None and c.estimate < 0.04
