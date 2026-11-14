"""Update-Knopf: neueste ``Boxenfunk.exe`` von der GitHub-Release-Seite laden und austauschen.

Die Einstellungen liegen getrennt von der exe (``%APPDATA%\\Boxenfunk``), bleiben also erhalten.
Weil Windows eine laufende exe nicht überschreiben lässt, schreibt Boxenfunk ein kleines
Hilfsskript, beendet sich, und das Skript tauscht die Datei aus und startet die neue Version.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO = "robertus01187/boxenfunk"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET = "Boxenfunk.exe"
TIMEOUT = 15


@dataclass
class Release:
    version: str
    url: str  # Download der exe
    page: str


def parse_version(v: str) -> tuple[int, ...]:
    v = v.strip().lstrip("vV")
    out = []
    for part in v.split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out)


def is_newer(remote: str, local: str) -> bool:
    try:
        return parse_version(remote) > parse_version(local)
    except ValueError:
        return False


def latest_release(opener: Callable = urllib.request.urlopen) -> Release | None:
    req = urllib.request.Request(
        API, headers={"User-Agent": "Boxenfunk-Updater", "Accept": "application/vnd.github+json"}
    )
    with opener(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8"))
    for a in data.get("assets", []):
        if a.get("name") == ASSET:
            return Release(
                version=data.get("tag_name", "").lstrip("v"),
                url=a["browser_download_url"],
                page=data.get("html_url", ""),
            )
    return None


def can_self_update() -> bool:
    """Nur die fertige Windows-exe kann sich selbst austauschen."""
    return bool(getattr(sys, "frozen", False)) and sys.platform == "win32"


def download(
    rel: Release, target: Path, progress: Callable[[int, int], None] | None = None
) -> None:
    req = urllib.request.Request(rel.url, headers={"User-Agent": "Boxenfunk-Updater"})
    tmp = target.with_suffix(target.suffix + ".teil")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if total and done != total:
        tmp.unlink(missing_ok=True)
        raise OSError("Download unvollständig")
    tmp.replace(target)


def swap_script(new_exe: Path, exe: Path) -> str:
    """Batch-Skript: wartet, bis Boxenfunk beendet ist, tauscht die exe und startet sie neu."""
    return (
        "@echo off\r\n"
        "set n=0\r\n"
        ":warte\r\n"
        "timeout /t 1 /nobreak >nul\r\n"
        "set /a n+=1\r\n"
        f'move /y "{new_exe}" "{exe}" >nul 2>&1 || (if %n% lss 60 goto warte)\r\n'
        f'start "" "{exe}"\r\n'
        '(goto) 2>nul & del "%~f0"\r\n'
    )


def install_and_restart(new_exe: Path) -> None:
    """Startet das Austausch-Skript. Danach muss sich Boxenfunk sofort beenden."""
    exe = Path(sys.executable).resolve()
    fd, bat = tempfile.mkstemp(prefix="boxenfunk-update-", suffix=".bat")
    with os.fdopen(fd, "w", encoding="mbcs" if sys.platform == "win32" else "utf-8") as f:
        f.write(swap_script(new_exe, exe))
    flags = 0x08000000 | 0x00000008  # CREATE_NO_WINDOW | DETACHED_PROCESS
    subprocess.Popen(["cmd", "/c", bat], creationflags=flags, close_fds=True)  # noqa: S603,S607
