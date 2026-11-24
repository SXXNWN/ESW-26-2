from pathlib import Path
import unittest

from santas_delivery.assets import AssetManager
from santas_delivery.game import Game
from santas_delivery.hardware import validate_hardware_config
from santas_delivery.renderer import Renderer

from helpers import ROOT


class ResourceHardwareTests(unittest.TestCase):
    def test_all_game_states_render_240_square(self) -> None:
        assets = AssetManager(ROOT / "assets")
        renderer = Renderer(assets)
        game = Game(ROOT)
        title = renderer.render(game)
        self.assertEqual(title.size, (240, 240))
        self.assertEqual(title.mode, "RGB")
        game.start_new_game()
        playing = renderer.render(game)
        self.assertEqual(playing.size, (240, 240))
        self.assertGreater(len(assets._cache), 8)

    def test_hud_preview_values_are_replaced_dynamically(self) -> None:
        assets = AssetManager(ROOT / "assets")
        renderer = Renderer(assets)
        game = Game(ROOT)
        game.start_new_game()
        game._load_stage(1)
        game.player.hp = 1
        frame = renderer.render(game)
        self.assertEqual(frame.getpixel((46, 12)), (31, 43, 86))
        base = assets.get("ui/hud_240x24.png").convert("RGB")
        self.assertNotEqual(frame.crop((156, 0, 240, 24)).tobytes(), base.crop((156, 0, 240, 24)).tobytes())

    def test_gameplay_background_image_is_hidden(self) -> None:
        from santas_delivery.constants import BACKGROUND_CLEAR_COLOR

        assets = AssetManager(ROOT / "assets")
        game = Game(ROOT)
        game.start_new_game()
        frame = Renderer(assets).render(game)
        self.assertEqual(frame.getpixel((0, 24)), BACKGROUND_CLEAR_COLOR)

    def test_title_background_image_is_hidden(self) -> None:
        from santas_delivery.constants import BACKGROUND_CLEAR_COLOR

        assets = AssetManager(ROOT / "assets")
        frame = Renderer(assets).render(Game(ROOT))
        self.assertEqual(frame.getpixel((0, 160)), BACKGROUND_CLEAR_COLOR)
        self.assertNotEqual(frame.getpixel((120, 80)), BACKGROUND_CLEAR_COLOR)

    def test_stage_clear_background_image_is_hidden(self) -> None:
        from santas_delivery.constants import BACKGROUND_CLEAR_COLOR
        from santas_delivery.game import GameState

        assets = AssetManager(ROOT / "assets")
        game = Game(ROOT)
        game.start_new_game()
        game.state = GameState.STAGE_CLEAR
        frame = Renderer(assets).render(game)
        self.assertEqual(frame.getpixel((0, 160)), BACKGROUND_CLEAR_COLOR)
        self.assertNotEqual(frame.getpixel((120, 120)), BACKGROUND_CLEAR_COLOR)

    def test_all_clear_background_image_is_hidden(self) -> None:
        from santas_delivery.constants import BACKGROUND_CLEAR_COLOR
        from santas_delivery.game import GameState

        assets = AssetManager(ROOT / "assets")
        game = Game(ROOT)
        game.state = GameState.ALL_CLEAR
        frame = Renderer(assets).render(game)
        self.assertEqual(frame.getpixel((0, 160)), BACKGROUND_CLEAR_COLOR)
        self.assertNotEqual(frame.getpixel((120, 120)), BACKGROUND_CLEAR_COLOR)

    def test_warning_background_image_is_hidden(self) -> None:
        from santas_delivery.constants import BACKGROUND_CLEAR_COLOR
        from santas_delivery.game import GameState

        assets = AssetManager(ROOT / "assets")
        game = Game(ROOT)
        game.state = GameState.WARNING
        frame = Renderer(assets).render(game)
        self.assertEqual(frame.getpixel((0, 160)), BACKGROUND_CLEAR_COLOR)
        self.assertNotEqual(frame.getpixel((120, 120)), BACKGROUND_CLEAR_COLOR)

    def test_game_over_background_image_is_hidden(self) -> None:
        from santas_delivery.constants import BACKGROUND_CLEAR_COLOR
        from santas_delivery.game import GameState

        assets = AssetManager(ROOT / "assets")
        game = Game(ROOT)
        game.state = GameState.GAME_OVER
        frame = Renderer(assets).render(game)
        self.assertEqual(frame.getpixel((0, 160)), BACKGROUND_CLEAR_COLOR)
        self.assertNotEqual(frame.getpixel((120, 120)), BACKGROUND_CLEAR_COLOR)

    def test_confirmed_adafruit_bonnet_config(self) -> None:
        config = validate_hardware_config(ROOT / "config" / "hardware.adafruit-tft-bonnet.json")
        self.assertEqual(config["lcd"]["controller"], "ST7789V")
        self.assertEqual(config["lcd"]["resolution"], [240, 240])
        self.assertEqual(config["joystick"]["pin_center"], 4)
        self.assertEqual(config["buttons"]["pin_a"], 5)
        self.assertEqual(config["buttons"]["pin_b"], 6)
