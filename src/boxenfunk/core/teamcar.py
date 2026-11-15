"""Teamauto beim Zuschauen: Wenn ein Teamkollege fährt, folgen die Overlays eurem Auto.

Wie TinyPedal: Das eigene Auto ist das mit ``mIsPlayer``. Findet TinyPedal keins (du schaust nur
zu), bleibt es beim zuletzt gefundenen Auto; zusätzlich kann man dort von Hand ein Auto wählen
(„Spectate mode“, Auswahl über die Slot-ID ``mID``). Boxenfunk macht beides:

- Automatisch: das Auto, in dem du zuletzt gesessen hast (Slot-ID, gespeichert, damit es auch nach
  einem Neustart von Boxenfunk klappt). LMU behält die Slot-ID über Training, Quali und Rennen.
- Von Hand: ein Auto aus der Liste im Boxenfunk-Fenster.

Beim Zuschauen liefert LMU vom Teamauto Platz, Runden, Zeiten, Abstände, Boxenstopps, Fahrer und
VE (nur in Schritten von 1/255). Sprit, Reifen und Eingaben kommen nicht an (Aufnahme 8h Bahrain).
"""

from __future__ import annotations

from boxenfunk.model.race_state import CarState, RaceState


def car_label(car: CarState) -> str:
    return f"{car.driver} · {car.team or car.model} ({car.car_class})"


class TeamCar:
    def __init__(self, saved: dict | None = None) -> None:
        saved = saved or {}
        self.car_id: str | None = saved.get("id")  # zuletzt selbst gefahren
        self.team: str = saved.get("team", "")
        self.manual: str | None = None  # von Hand gewählt (gilt nur bis zum Neustart)
        self.changed = False  # gemerktes Auto hat sich geändert → speichern

    def to_cfg(self) -> dict:
        return {"id": self.car_id, "team": self.team}

    def apply(self, st: RaceState) -> RaceState:
        """Setzt beim Zuschauen das Teamauto als „mein Auto“ und markiert ``st.spectating``."""
        me = st.player_car()
        if me is not None:
            if (me.car_id, me.team) != (self.car_id, self.team):
                self.car_id, self.team = me.car_id, me.team
                self.changed = True
            return st
        target = self.manual or self.car_id
        if target is None:
            return st
        car = next((c for c in st.cars if c.car_id == target), None)
        if car is None:
            return st
        # Automatisch nur, wenn der Slot noch zum selben Team gehört (andere Session/Server)
        if not self.manual and self.team and car.team != self.team:
            return st
        st.player_id = car.car_id
        st.spectating = True
        car.is_player = True  # Zeile hervorheben und in die Mitte setzen wie beim eigenen Auto
        return st
