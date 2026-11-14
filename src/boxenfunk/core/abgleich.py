"""Abgleich: Rechnen die Overlays dasselbe wie das Spiel?

Spielt eine Aufnahme ab, berechnet alles wie die Overlays und vergleicht mit den Werten, die
LMU selbst ausrechnet (eigenes Auto: ``mTimeGapCarAhead/Behind`` = Abstand auf der Strecke,
``mTimeGapPlaceAhead`` = Abstand zum Platz davor).

Aufruf: ``python -m boxenfunk.core.abgleich <Aufnahme-Datei oder Ordner>``
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from boxenfunk.adapters.lmu.translate import to_race_state
from boxenfunk.core.tracker import SessionTracker
from boxenfunk.core.views import gap_between
from boxenfunk.model.race_state import Phase
from boxenfunk.recorder.delta import DeltaDecoder
from boxenfunk.recorder.files import read_lines, recording_files


@dataclass
class Vergleich:
    name: str
    diffs: list[float] = field(default_factory=list)

    def add(self, ours: float | None, game: float | None) -> None:
        if ours is None or game is None:
            return
        self.diffs.append(abs(abs(ours) - abs(game)))

    def zeile(self) -> str:
        if not self.diffs:
            return f"{self.name:<34} keine Werte"
        d = sorted(self.diffs)
        q = lambda f: d[min(len(d) - 1, int(len(d) * f))]  # noqa: E731
        unter = sum(1 for x in d if x <= 0.2) / len(d) * 100
        return (
            f"{self.name:<34} {len(d):>7}  Mitte {q(0.5):5.2f} s  90 % {q(0.9):5.2f} s  "
            f"max {d[-1]:5.1f} s  bis 0,2 s: {unter:4.0f} %"
        )


def abgleich(path: Path) -> list[Vergleich]:
    rel_vor = Vergleich("Relative: Auto vor mir")
    rel_hinter = Vergleich("Relative: Auto hinter mir")
    platz_vor = Vergleich("Standings: Abstand Platz davor")
    tr = SessionTracker()
    dec = DeltaDecoder()
    for f in recording_files(path):
        for line in read_lines(f):
            if line.get("typ"):
                continue
            snap = dec.apply(line)
            if not snap or not snap["c"]:
                continue
            st = to_race_state(snap)
            tr.update(st)
            me = st.player_car()
            if me is None or me.in_pits or st.phase != Phase.GRUEN:
                continue
            raw = snap["c"][me.car_id].get("v", {})
            rel = tr.relative(st, 1, 1)
            i = next((k for k, e in enumerate(rel) if e.car.is_player), None)
            if i is None:
                continue
            # Das Spiel überspringt Autos in der Box
            if i > 0 and not rel[i - 1].car.in_pits:
                rel_vor.add(rel[i - 1].gap, raw.get("mTimeGapCarAhead"))
            if i + 1 < len(rel) and not rel[i + 1].car.in_pits:
                rel_hinter.add(rel[i + 1].gap, raw.get("mTimeGapCarBehind"))
            if me.position > 1:
                ahead = st.cars[me.position - 2]
                g = gap_between(st, me, ahead)
                if g and not g.endswith("L"):
                    platz_vor.add(float(g), raw.get("mTimeGapPlaceAhead"))
    return [rel_vor, rel_hinter, platz_vor]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Overlay-Werte mit den Spielwerten vergleichen")
    ap.add_argument("aufnahme", type=Path)
    args = ap.parse_args(argv)
    print(f"Abgleich mit {args.aufnahme} (nur grüne Flagge, eigenes Auto nicht in der Box)")
    for v in abgleich(args.aufnahme):
        print(v.zeile())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
