"""Live-Quelle (über einen Test-Speicherbereich) und Update-Knopf (ohne Internet)."""

from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

from fake_lmu import FakeLmu

from boxenfunk import updater
from boxenfunk.adapters.lmu import shm
from boxenfunk.adapters.sources import LmuLiveSource


def test_live_source_full_and_fast_inputs():
    name = f"Boxenfunk_Test_{uuid.uuid4().hex[:8]}"
    fake = FakeLmu()
    fake.tick(5)
    tel = fake.data.telemetry
    idx = len(fake.cars) - 1 - 4  # Fake legt Telemetrie in umgekehrter Reihenfolge ab
    tel.playerHasVehicle = 1
    tel.playerVehicleIdx = idx
    mm = shm._open(name, shm.SIZE)
    mm[:] = bytes(fake.data)
    try:
        src = LmuLiveSource(name)
        st = src.poll()
        assert st is not None and st.player is not None
        assert "LMU verbunden" in src.status
        assert src.poll_inputs(st.player) is False  # gleiche Spielzeit, nichts Neues
        fake.data.telemetry.telemInfo[idx].mElapsedTime += 0.02
        fake.data.telemetry.telemInfo[idx].mFilteredThrottle = 0.75
        fake.data.telemetry.telemInfo[idx].mGear = 4
        mm[:] = bytes(fake.data)
        assert src.poll_inputs(st.player) is True
        assert st.player.throttle == 0.75 and st.player.gear == 4
    finally:
        mm.close()
        Path(f"/dev/shm/{name}").unlink(missing_ok=True)


def test_versions():
    assert updater.parse_version("v0.3.10") == (0, 3, 10)
    assert updater.is_newer("0.3.1", "0.3.0")
    assert updater.is_newer("v1.0.0", "0.9.9")
    assert not updater.is_newer("0.3.0", "0.3.0")
    assert not updater.is_newer("0.2.9", "0.3.0")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_latest_release_picks_overlay_exe():
    data = {
        "tag_name": "v0.4.0",
        "html_url": "https://example.invalid/r",
        "assets": [
            {"name": "Boxenfunk-LMU-Recorder.exe", "browser_download_url": "x"},
            {"name": "Boxenfunk.exe", "browser_download_url": "https://example.invalid/B.exe"},
        ],
    }
    rel = updater.latest_release(lambda req, timeout: _Resp(json.dumps(data).encode()))
    assert rel.version == "0.4.0" and rel.url.endswith("B.exe")


def test_swap_script_replaces_and_restarts():
    s = updater.swap_script(Path("C:/B/Boxenfunk.neu.exe"), Path("C:/B/Boxenfunk.exe"))
    assert "move /y" in s and "Boxenfunk.neu.exe" in s and 'start ""' in s
    assert not updater.can_self_update()  # Tests laufen nie als fertige exe
