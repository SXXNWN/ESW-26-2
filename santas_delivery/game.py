from __future__ import annotations

from enum import Enum
from pathlib import Path

from .constants import ATTACK_COOLDOWN, DELIVERY_FEET_RANGE, DELIVERY_RANGE_X, ENABLE_ICE_ZONES
from .entities import Boss, Camera, Enemy, FallingIcicle, Player, Projectile
from .geometry import Rect
from .input import InputFrame
from .stage import Stage, build_stage, load_stage_specs


class GameState(str, Enum):
    TITLE = "TITLE"
    PLAYING = "PLAYING"
    STAGE_CLEAR = "STAGE_CLEAR"
    WARNING = "WARNING"
    BOSS_FIGHT = "BOSS_FIGHT"
    GAME_OVER = "GAME_OVER"
    ALL_CLEAR = "ALL_CLEAR"


class Game:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[1]
        self.stage_specs = load_stage_specs(self.root / "config" / "stages.json")
        self.state = GameState.TITLE
        self.stage_index = 0
        self.stage: Stage | None = None
        self.player: Player | None = None
        self.camera = Camera()
        self.running = True
        self.state_timer = 0.0
        self.message = ""
        self.message_timer = 0.0
        self.boss_defeated = False
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.icicles: list[FallingIcicle] = []
        self.boss: Boss | None = None
        self.gift_effects: list[dict[str, float]] = []

    def start_new_game(self) -> None:
        self.stage_index = 0
        self._load_stage(0)

    def _load_stage(self, index: int) -> None:
        self.stage_index = index
        self.stage = build_stage(self.stage_specs[index])
        spawn = self.stage.player_spawn
        self.player = Player(float(spawn["x"]), float(spawn["y"]))
        self.camera = Camera()
        self.camera.follow(self.player, self.stage.world_width)
        self.boss_defeated = False
        self.enemies = [
            Enemy(
                id=item["id"],
                kind=item["type"],
                x=float(item["x"]),
                y=float(item["y"]),
                patrol_min_x=float(item["patrol_min_x"]),
                patrol_max_x=float(item["patrol_max_x"]),
                hp=int(item["hp"]),
            )
            for item in self.stage.enemy_specs
        ]
        self.projectiles = []
        self.gift_effects = []
        self.icicles = [
            FallingIcicle(float(item["x"]), float(item["y"]), float(item["trigger_distance"]))
            for item in self.stage.obstacle_specs
            if item["type"] == "icicle"
        ]
        if self.stage.boss_spec:
            item = self.stage.boss_spec
            self.boss = Boss(float(item["x"]), float(item["y"]), int(item["hp"]), int(item["hp"]))
        else:
            self.boss = None
        self.message = ""
        self.message_timer = 0.0
        self.state = GameState.PLAYING

    def update(self, controls: InputFrame, dt: float) -> None:
        dt = min(max(dt, 0.0), 0.05)
        if controls.quit:
            self.running = False
            return
        if self.state == GameState.TITLE:
            if controls.pressed("start") or controls.pressed("action_a"):
                self.start_new_game()
            return
        if self.state == GameState.GAME_OVER:
            if controls.pressed("start"):
                self.start_new_game()
            return
        if self.state == GameState.ALL_CLEAR:
            if controls.pressed("start"):
                self.state = GameState.TITLE
            return
        if self.state == GameState.STAGE_CLEAR:
            self.state_timer -= dt
            if self.state_timer <= 0 or controls.pressed("start"):
                self._load_stage(self.stage_index + 1)
            return
        if self.state == GameState.WARNING:
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = GameState.BOSS_FIGHT
                if self.boss:
                    self.boss.active = True
            return
        self._update_playing(controls, dt)

    def _update_playing(self, controls: InputFrame, dt: float) -> None:
        assert self.stage is not None and self.player is not None
        self.message_timer = max(0.0, self.message_timer - dt)
        if self.message_timer == 0:
            self.message = ""
        on_ice = ENABLE_ICE_ZONES and any(
            zone["x1"] <= self.player.x + 16 <= zone["x2"] for zone in self.stage.ice_zones
        )
        old_x, old_y = self.player.x, self.player.y
        self.player.update(controls, dt, self.stage.ground_y, self.stage.world_width, on_ice)
        self._resolve_crates(old_x, old_y)

        if controls.pressed("action_a"):
            self.try_delivery()
        if controls.action_b:
            self.try_attack()

        self._update_enemies(dt)
        self._update_icicles(dt)
        self._update_boss(dt)
        self._update_projectiles(dt)
        self._resolve_combat()
        for effect in self.gift_effects:
            effect["time"] -= dt
            effect["y"] -= 18.0 * dt
        self.gift_effects = [effect for effect in self.gift_effects if effect["time"] > 0]

        if self.stage.id == 3 and self.stage.boss_spec and not self.boss_defeated:
            boss = self.stage.boss_spec
            if self.player.x >= boss["warning_trigger_x"]:
                if self.stage.normal_delivery_count < self.stage.normal_delivery_goal:
                    self.player.x = boss["warning_trigger_x"] - 1
                    self.message = "DELIVER 3 GIFTS FIRST!"
                    self.message_timer = 1.2
                elif self.state == GameState.PLAYING:
                    self.state = GameState.WARNING
                    self.state_timer = 1.5

            if self.state == GameState.BOSS_FIGHT and self.player.x > boss["arena_right_x"] - 32:
                self.player.x = boss["arena_right_x"] - 32
                self.player.vx = min(0.0, self.player.vx)

        self.camera.follow(self.player, self.stage.world_width)
        if self.stage.exit_x is not None and self.player.x >= self.stage.exit_x:
            if self.stage.all_delivered():
                self.state = GameState.STAGE_CLEAR
                self.state_timer = 1.5
            else:
                self.message = "DELIVER ALL GIFTS!"
                self.message_timer = 1.0
        if self.player.hp <= 0:
            self.state = GameState.GAME_OVER

    def _resolve_crates(self, old_x: float, old_y: float) -> None:
        assert self.stage is not None and self.player is not None
        for item in self.stage.obstacle_specs:
            if item["type"] != "crate":
                continue
            crate = Rect(float(item["x"]), float(item["y"]), 16, 16)
            if not self.player.hitbox.intersects(crate):
                continue
            old_feet = old_y + 32
            if old_feet <= crate.top + 2 and self.player.vy >= 0:
                self.player.y = crate.top - 32
                self.player.vy = 0
                self.player.on_ground = True
            elif self.player.vx > 0:
                self.player.x = crate.left - 26
                self.player.vx = 0
            elif self.player.vx < 0:
                self.player.x = crate.right - 6
                self.player.vx = 0
            else:
                self.player.x = old_x

    def try_attack(self) -> bool:
        assert self.player is not None
        if self.player.attack_cooldown > 0:
            return False
        direction = self.player.facing
        spawn_x = self.player.x + (25 if direction > 0 else -1)
        self.projectiles.append(Projectile(spawn_x, self.player.y + 10, direction * 190.0, 0, "player"))
        self.player.attack_cooldown = ATTACK_COOLDOWN
        self.player.action = "attack"
        self.player.action_timer = 0.28
        return True

    def _update_enemies(self, dt: float) -> None:
        assert self.player is not None
        for enemy in self.enemies:
            if enemy.update(self.player, dt):
                direction = 1 if self.player.x > enemy.x else -1
                self.projectiles.append(
                    Projectile(enemy.x + (24 if direction > 0 else 0), enemy.y + 4, direction * 90.0, 0, "enemy")
                )

    def _update_icicles(self, dt: float) -> None:
        assert self.player is not None and self.stage is not None
        for icicle in self.icicles:
            icicle.update(self.player, self.stage.ground_y, dt)

    def _update_boss(self, dt: float) -> None:
        assert self.player is not None
        if self.boss and self.boss.update(dt):
            direction = 1 if self.player.x > self.boss.x else -1
            self.projectiles.append(
                Projectile(
                    self.boss.x + (52 if direction > 0 else -4),
                    self.boss.y + 32,
                    direction * 115.0,
                    0,
                    "boss",
                    size=16,
                    life=5.0,
                )
            )

    def _update_projectiles(self, dt: float) -> None:
        assert self.stage is not None
        crates = [
            Rect(float(item["x"]), float(item["y"]), 16, 16)
            for item in self.stage.obstacle_specs
            if item["type"] == "crate"
        ]
        for projectile in self.projectiles:
            projectile.update(dt)
            if any(projectile.hitbox.intersects(crate) for crate in crates):
                projectile.life = 0
            if projectile.x < -32 or projectile.x > self.stage.world_width + 32:
                projectile.life = 0
        self.projectiles = [p for p in self.projectiles if p.life > 0]

    def _resolve_combat(self) -> None:
        assert self.player is not None
        for projectile in self.projectiles:
            if projectile.owner == "player":
                hit = False
                for enemy in self.enemies:
                    if enemy.alive and projectile.hitbox.intersects(enemy.hitbox):
                        enemy.hp -= projectile.damage
                        projectile.life = 0
                        hit = True
                        break
                if not hit and self.boss and self.boss.active and not self.boss.defeated:
                    if projectile.hitbox.intersects(self.boss.hitbox):
                        self.boss.hp -= projectile.damage
                        projectile.life = 0
                        if self.boss.hp <= 0:
                            self.boss.hp = 0
                            self.boss.defeated = True
                            self.boss.active = False
                            self.boss_defeated = True
                            self.message = "BOSS DEFEATED! FINAL GIFT OPEN!"
                            self.message_timer = 2.0
            elif projectile.hitbox.intersects(self.player.hitbox):
                if self.player.damage(projectile.damage):
                    projectile.life = 0
        self.projectiles = [p for p in self.projectiles if p.life > 0]
        for enemy in self.enemies:
            if enemy.alive and enemy.hitbox.intersects(self.player.hitbox):
                self.player.damage()
        if self.boss and self.boss.active and self.boss.hitbox.intersects(self.player.hitbox):
            self.player.damage()
        for icicle in self.icicles:
            if icicle.state == "falling" and icicle.hitbox.intersects(self.player.hitbox):
                if self.player.damage():
                    icicle.state = "spent"

    def try_delivery(self) -> bool:
        assert self.stage is not None and self.player is not None
        player_center = self.player.x + 16
        for chimney in self.stage.chimneys:
            if chimney.delivered:
                continue
            if chimney.requires_boss_defeated and not self.boss_defeated:
                if abs(player_center - (chimney.x + 16)) <= DELIVERY_RANGE_X:
                    self.message = "LOCKED - DEFEAT BOSS!"
                    self.message_timer = 1.0
                continue
            close_x = abs(player_center - (chimney.x + 16)) <= DELIVERY_RANGE_X
            close_y = abs(self.player.feet_y - (chimney.y + 32)) <= DELIVERY_FEET_RANGE
            if close_x and close_y:
                chimney.delivered = True
                self.gift_effects.append({"x": chimney.x + 8, "y": chimney.y - 4, "time": 0.55})
                self.player.action = "deliver"
                self.player.action_timer = 0.45
                if self.stage.id == 3 and chimney.kind == "final" and self.boss_defeated:
                    self.state = GameState.ALL_CLEAR
                return True
        return False
