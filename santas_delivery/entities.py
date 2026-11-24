from dataclasses import dataclass
from .constants import GRAVITY, INVULNERABILITY_TIME, PLAYER_JUMP_SPEED, PLAYER_SPEED
from .geometry import Rect, clamp
from .input import InputFrame


@dataclass
class Player:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    facing: int = 1
    hp: int = 3
    on_ground: bool = True
    crouching: bool = False
    invulnerable: float = 0.0
    attack_cooldown: float = 0.0

    @property
    def hitbox(self) -> Rect:
        if self.crouching:
            return Rect(self.x + 6, self.y + 15, 20, 17)
        return Rect(self.x + 6, self.y + 3, 20, 29)

    def update(self, controls: InputFrame, dt: float, ground_y: float, world_width: float) -> None:
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.crouching = controls.down and self.on_ground

        direction = int(controls.right) - int(controls.left)
        if direction:
            self.facing = direction
        target = direction * PLAYER_SPEED * (0.42 if self.crouching else 1.0)
        self.vx = target

        if controls.pressed("up") and self.on_ground and not self.crouching:
            self.vy = PLAYER_JUMP_SPEED
            self.on_ground = False

        self.vy += GRAVITY * dt
        self.x = clamp(self.x + self.vx * dt, 0.0, world_width - 32)
        self.y += self.vy * dt
        if self.y + 32 >= ground_y:
            self.y = ground_y - 32
            self.vy = 0.0
            self.on_ground = True

    def damage(self, amount: int = 1) -> bool:
        if self.invulnerable > 0 or self.hp <= 0:
            return False
        self.hp = max(0, self.hp - amount)
        self.invulnerable = INVULNERABILITY_TIME
        return True


@dataclass
class Camera:
    x: float = 0.0

    def follow(self, player: Player, world_width: float) -> None:
        self.x = clamp(player.x + 16 - 120, 0, max(0, world_width - 240))

@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    owner: str
    size: int = 8
    life: float = 4.0

    @property
    def hitbox(self) -> Rect:
        return Rect(self.x, self.y, self.size, self.size)

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.life -= dt


@dataclass
class Enemy:
    kind: str
    x: float
    y: float
    patrol_min_x: float
    patrol_max_x: float
    hp: int
    direction: int = 1
    shoot_timer: float = 1.55

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def hitbox(self) -> Rect:
        return Rect(self.x + 5, self.y + 4, 22, 28)

    def update(self, player: Player, dt: float) -> bool:
        if not self.alive:
            return False
        speed = 24.0 if self.kind == "walker" else 12.0
        self.x += self.direction * speed * dt
        if self.x <= self.patrol_min_x:
            self.x = self.patrol_min_x
            self.direction = 1
        elif self.x >= self.patrol_max_x:
            self.x = self.patrol_max_x
            self.direction = -1
        if abs(player.x - self.x) < 220:
            self.direction = 1 if player.x > self.x else -1
        if self.kind != "ranged":
            return False
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 1.55
            return True
        return False

@dataclass
class Boss:
    x: float
    y: float
    hp: int
    max_hp: int
    active: bool = False
    defeated: bool = False
    attack_timer: float = 1.65

    @property
    def hitbox(self) -> Rect:
        return Rect(self.x + 8, self.y + 7, 48, 57)

    def update(self, dt: float) -> bool:
        if not self.active or self.defeated:
            return False
        self.attack_timer -= dt
        if self.attack_timer <= 0:
            self.attack_timer = 1.65
            return True
        return False
