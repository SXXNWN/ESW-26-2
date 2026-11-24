from pathlib import Path

from santas_delivery.game import Game
from santas_delivery.input import InputFrame


ROOT = Path(__file__).resolve().parents[1]
DT = 1 / 60


def edge(name: str) -> InputFrame:
    values = {name: True, "just_pressed": frozenset({name})}
    return InputFrame(**values)


def started_game() -> Game:
    game = Game(ROOT)
    game.update(edge("start"), DT)
    return game
