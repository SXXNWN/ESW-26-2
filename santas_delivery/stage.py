import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .geometry import Rect


@dataclass
class Chimney:
    x: float
    y: float
    requires_boss_defeated: bool = False
    delivered: bool = False


@dataclass
class Stage:
    id: int
    world_width: int
    ground_y: int
    player_spawn: dict[str, float]
    exit_x: float | None
    chimneys: list[Chimney]
    enemy_specs: list[dict[str, Any]]
    crates: list[Rect]
    boss_spec: dict[str, Any] | None

    @property
    def delivery_count(self) -> int:
        return sum(chimney.delivered for chimney in self.chimneys)

    @property
    def delivery_goal(self) -> int:
        return len(self.chimneys)

    @property
    def normal_delivery_count(self) -> int:
        return sum(c.delivered for c in self.chimneys if not c.requires_boss_defeated)

    @property
    def normal_delivery_goal(self) -> int:
        return sum(not c.requires_boss_defeated for c in self.chimneys)

def load_stage_specs(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("screen") != {"width": 240, "height": 240}:
        raise ValueError("stages.json의 화면 크기는 240×240이어야 합니다")
    return data["stages"]


def build_stage(spec: dict[str, Any]) -> Stage:
    ground_y = spec["ground_y"]
    chimneys = [Chimney(x, ground_y - 32) for x in spec["chimneys"]]
    if spec["boss"]:
        chimneys.append(Chimney(spec["final_chimney"], ground_y - 32, True))
    return Stage(
        id=spec["id"],
        world_width=spec["world_width"],
        ground_y=spec["ground_y"],
        player_spawn=dict(spec["player_spawn"]),
        exit_x=spec["exit_x"],
        chimneys=chimneys,
        enemy_specs=[dict(item) for item in spec["enemies"]],
        crates=[Rect(x, ground_y - 16, 16, 16) for x in spec["crates"]],
        boss_spec=dict(spec["boss"]) if spec["boss"] else None,
    )
