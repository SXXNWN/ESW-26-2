from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def intersects(self, other: "Rect") -> bool:
        return (
            self.x < other.x + other.w
            and self.x + self.w > other.x
            and self.y < other.y + other.h
            and self.y + self.h > other.y
        )


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
