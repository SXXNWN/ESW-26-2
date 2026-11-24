from PIL import Image, ImageDraw, ImageFont, ImageOps

from .assets import AssetManager
from .constants import (
    BACKGROUND_CLEAR_COLOR,
    HUD_HEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .game import Game, GameState

BADGES = {
    GameState.STAGE_CLEAR: ("ui/clear_badge.png", 2),
    GameState.ALL_CLEAR: ("ui/all_clear_badge.png", 1),
    GameState.WARNING: ("ui/warning_badge.png", 1),
    GameState.GAME_OVER: ("ui/game_over_badge.png", 1),
}


class Renderer:
    def __init__(self, assets: AssetManager) -> None:
        self.assets = assets
        self.font = ImageFont.load_default()
        self._blank_frame = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), BACKGROUND_CLEAR_COLOR)
        self._base_frame = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "black")
        self._base_frame.paste(BACKGROUND_CLEAR_COLOR, (0, HUD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT))
        self._boss_sprite = self.assets.get("boss/boss.gif").resize((64, 64), Image.Resampling.NEAREST)
        self._player_sprite = self.assets.get("player/santa.gif").resize((64, 64), Image.Resampling.NEAREST)
        self._logo = self.assets.get("ui/logo.gif").resize((224, 224), Image.Resampling.NEAREST)

    def render(self, game: Game) -> Image.Image:
        if game.state == GameState.TITLE:
            frame = self._blank_frame.copy()
            frame.paste(self._logo, (8, 0), self._logo)
            draw = ImageDraw.Draw(frame)
            prompt = "PRESS ANY BUTTON"
            bounds = draw.textbbox((0, 0), prompt, font=self.font)
            draw.rectangle((24, 204, 216, 229), fill=(20, 38, 75), outline=(245, 245, 255))
            draw.text(((SCREEN_WIDTH - (bounds[2] - bounds[0])) // 2, 210), prompt, fill="white", font=self.font)
            return frame
        if game.state in BADGES:
            path, scale = BADGES[game.state]
            badge = self.assets.get(path)
            if scale > 1:
                badge = badge.resize((badge.width * scale, badge.height * scale), Image.Resampling.NEAREST)
            frame = self._blank_frame.copy()
            frame.paste(badge, ((SCREEN_WIDTH - badge.width) // 2, (SCREEN_HEIGHT - badge.height) // 2), badge)
            return frame
        assert game.stage is not None and game.player is not None
        frame = self._base_frame.copy()
        self._draw_world(frame, game)
        self._draw_hud(frame, game)
        return frame

    def _paste_world(self, frame: Image.Image, image: Image.Image, x: float, y: float, game: Game, flip: bool = False) -> None:
        sx = round(x - game.camera.x)
        sy = round(y) + HUD_HEIGHT
        if sx < SCREEN_WIDTH and sx + image.width > 0 and sy < SCREEN_HEIGHT and sy + image.height > HUD_HEIGHT:
            sprite = ImageOps.mirror(image) if flip else image
            frame.paste(sprite, (sx, sy), sprite if sprite.mode == "RGBA" else None)

    def _draw_world(self, frame: Image.Image, game: Game) -> None:
        assert game.stage is not None and game.player is not None
        stage = game.stage
        boss_stage = bool(stage.boss_spec)
        top_tile = "tiles/stone_floor.png" if boss_stage else "tiles/roof_snow.png"
        fill_tile = "tiles/roof_brick.png"
        first_x = int(game.camera.x // 16) * 16
        for x in range(first_x, int(game.camera.x) + SCREEN_WIDTH + 16, 16):
            self._paste_world(frame, self.assets.get(top_tile), x, stage.ground_y, game)
            for y in range(stage.ground_y + 16, 216, 16):
                self._paste_world(frame, self.assets.get(fill_tile), x, y, game)
        decor_name = "decor/fence.png" if boss_stage else "decor/streetlamp.png"
        decor_step = 256 if boss_stage else 208
        decor_y = stage.ground_y - self.assets.get(decor_name).height
        for x in range(96, stage.world_width, decor_step):
            self._paste_world(frame, self.assets.get(decor_name), x, decor_y, game)
        for chimney in stage.chimneys:
            name = "objects/chimney_delivered.png" if chimney.delivered else "objects/chimney_unfilled.png"
            self._paste_world(frame, self.assets.get(name), chimney.x, chimney.y, game)
        for crate in stage.crates:
            self._paste_world(frame, self.assets.get("tiles/wood_crate.png"), crate.x, crate.y, game)
        for enemy in game.enemies:
            if not enemy.alive:
                continue
            self._paste_world(
                frame, self.assets.get("enemies/snowman_idle.png"), enemy.x, enemy.y, game, enemy.direction < 0
            )
        if game.boss and not game.boss.defeated:
            self._paste_world(frame, self._boss_sprite, game.boss.x, game.boss.y, game)
        if game.boss and game.boss.active and not game.boss.defeated and stage.boss_spec:
            gate_x = stage.boss_spec["arena_right_x"]
            for gate_y in range(120, stage.ground_y, 16):
                self._paste_world(frame, self.assets.get("tiles/roof_brick.png"), gate_x, gate_y, game)
        for projectile in game.projectiles:
            name = "items/snowball_large_16.png" if projectile.size == 16 else "items/snowball_08.png"
            self._paste_world(frame, self.assets.get(name), projectile.x, projectile.y, game)
        for effect in game.gift_effects:
            self._paste_world(frame, self.assets.get("items/gift_box.png"), effect["x"], effect["y"], game)
        player = game.player
        hide_player = player.invulnerable > 0 and int(player.invulnerable * 12) % 2 == 0
        if not hide_player:
            self._paste_world(frame, self._player_sprite, player.x - 16, player.y - 32, game, player.facing < 0)
        if game.boss and game.boss.active and not game.boss.defeated:
            draw = ImageDraw.Draw(frame)
            draw.rectangle((51, 27, 189, 32), fill=(30, 30, 50), outline="white")
            width = int(136 * game.boss.hp / game.boss.max_hp)
            draw.rectangle((52, 28, 52 + width, 31), fill=(210, 45, 55))
        if game.message:
            draw = ImageDraw.Draw(frame)
            box = draw.textbbox((0, 0), game.message, font=self.font)
            width = box[2] - box[0]
            draw.rectangle((4, 30, 236, 44), fill=(20, 38, 75), outline=(245, 245, 255))
            draw.text(((240 - width) // 2, 33), game.message, fill="white", font=self.font)

    def _draw_hud(self, frame: Image.Image, game: Game) -> None:
        assert game.stage is not None and game.player is not None
        hud = self.assets.get("ui/hud_240x24.png")
        frame.paste(hud, (0, 0), hud)
        draw = ImageDraw.Draw(frame)
        hud_fill = (31, 43, 86)
        draw.rectangle((0, 0, 60, 23), fill=hud_fill)
        draw.rectangle((80, 0, 144, 23), fill=hud_fill)
        draw.rectangle((156, 0, 239, 23), fill=hud_fill)
        heart = self.assets.get("items/heart.png")
        for i in range(game.player.hp):
            frame.paste(heart, (4 + i * 17, 4), heart)
        gift = self.assets.get("items/gift_box.png")
        frame.paste(gift, (83, 4), gift)
        draw.text((101, 7), f"{game.stage.delivery_count}/{game.stage.delivery_goal}", font=self.font, fill="white")
        draw.text((164, 7), f"STAGE {game.stage.id}", font=self.font, fill="white")
