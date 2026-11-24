from dataclasses import dataclass


BUTTONS = ("left", "right", "up", "down", "action_a", "action_b", "start")


@dataclass(frozen=True)
class InputFrame:
    left: bool = False
    right: bool = False
    up: bool = False
    down: bool = False
    action_a: bool = False
    action_b: bool = False
    start: bool = False
    just_pressed: frozenset[str] = frozenset()

    def pressed(self, name: str) -> bool:
        return name in self.just_pressed


class InputTracker:
    def __init__(self) -> None:
        self._previous = {name: False for name in BUTTONS}

    def frame(self, **states: bool) -> InputFrame:
        current = {name: bool(states.get(name, False)) for name in BUTTONS}
        pressed = frozenset(name for name in BUTTONS if current[name] and not self._previous[name])
        self._previous = current
        return InputFrame(**current, just_pressed=pressed)
