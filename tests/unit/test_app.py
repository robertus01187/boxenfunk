import pytest

from boxenfunk import __version__, app


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        app.parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_main_quits_by_itself(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert app.main(["--quit-after", "50"]) == 0
