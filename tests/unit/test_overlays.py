"""Overlays zeichnen sich ohne Fehler, mit und ohne Daten, gesperrt und im Verschiebe-Modus."""

from __future__ import annotations

from pathlib import Path

from fake_lmu import FakeLmu

from boxenfunk.adapters.lmu.translate import to_race_state
from boxenfunk.core.tracker import SessionTracker
from boxenfunk.overlay.controller import Controller
from boxenfunk.overlay.widgets import ALL_OVERLAYS
from boxenfunk.recorder.snapshot import snapshot


class FakeSource:
    def __init__(self) -> None:
        self.fake = FakeLmu()
        self.t = 0.0
        self.status = "Test"

    def poll_inputs(self, pl):
        return False

    def poll(self):
        self.fake.tick(0.5)
        self.t += 0.5
        snap = snapshot(self.fake.data)
        snap["t"] = self.t
        return to_race_state(snap)


def test_overlays_paint(qtbot):
    src = FakeSource()
    tr = SessionTracker()
    for _ in range(600):
        st = src.poll()
        tr.update(st)
    for cls in ALL_OVERLAYS:
        o = cls()
        qtbot.addWidget(o)
        assert not o.grab().isNull()  # ohne Daten
        o.set_data(st, tr)
        assert o.width() > 50 and o.height() > 30
        assert not o.grab().isNull()
        o.set_locked(False)
        assert not o.grab().isNull()


def test_controller_runs_and_saves_positions(qtbot, tmp_path: Path):
    cfg = tmp_path / "cfg.json"
    ctl = Controller(FakeSource(), cfg, tmp_path / "logos")
    qtbot.addWidget(ctl.window)
    ctl.show()
    for _ in range(5):
        ctl.tick()
    assert ctl.has_data
    assert all(o.isVisible() for o in ctl.overlays)
    ctl.overlays[0].move(123, 45)
    ctl._toggle("delta", False)
    assert not ctl.overlays[2].isVisible()
    ctl.close()
    ctl2 = Controller(FakeSource(), cfg, tmp_path / "logos")
    qtbot.addWidget(ctl2.window)
    assert ctl2.overlays[0].pos().toTuple() == (123, 45)
    assert ctl2.enabled["delta"] is False
    ctl2.close()


def test_recording_button_writes_files(qtbot, tmp_path: Path):
    import time

    from boxenfunk.recorder import recorder
    from boxenfunk.recorder.files import recording_files

    class Moving(FakeLmu):
        def update(self) -> bool:
            self.tick(0.2)
            return True

    def factory(folder, log):
        return recorder.Recorder(Moving(), folder, hz=50, log=log)

    rec_dir = tmp_path / "Boxenfunk-Aufnahmen"
    ctl = Controller(
        FakeSource(),
        tmp_path / "cfg.json",
        tmp_path / "logos",
        recorder_factory=factory,
        rec_dir=rec_dir,
    )
    qtbot.addWidget(ctl.window)
    ctl.rec_btn.setChecked(True)
    assert ctl.recording.running
    time.sleep(0.5)
    ctl.tick()
    assert "Messpunkte" in ctl.rec_label.text()
    ctl.rec_btn.setChecked(False)
    assert not ctl.recording.running
    assert "gespeichert" in ctl.rec_label.text()
    assert len(recording_files(rec_dir)) == 1
    ctl.close()
