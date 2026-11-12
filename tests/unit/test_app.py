import pytest

from boxenfunk import __version__, app


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        app.parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_window_shows_status(qtbot):
    window = app.build_window()
    qtbot.addWidget(window)
    window.show()
    assert __version__ in window.windowTitle()
    from PySide6.QtWidgets import QLabel

    label = window.findChild(QLabel, "statusLabel")
    assert label is not None
    assert "läuft" in label.text()


def test_main_quits_by_itself(qapp):
    assert app.main(["--quit-after", "50"]) == 0
