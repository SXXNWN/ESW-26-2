from pathlib import Path
import unittest

from santas_delivery.assets import AssetManager
from santas_delivery.game import Game, GameState
from santas_delivery.input import InputTracker
from santas_delivery.renderer import Renderer


ROOT = Path(__file__).resolve().parents[1]


class MinimumGameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game(ROOT)
        self.input = InputTracker()
        self.game.update(self.input.frame(start=True), 1 / 60)

    def test_title_starts_stage_one(self) -> None:
        self.assertEqual(self.game.state, GameState.PLAYING)
        self.assertEqual(self.game.stage.id, 1)

    def test_movement_and_camera(self) -> None:
        for _ in range(180):
            self.game.update(self.input.frame(right=True), 1 / 60)
        self.assertGreater(self.game.player.x, 300)
        self.assertGreater(self.game.camera.x, 0)

    def test_jump_is_edge_triggered(self) -> None:
        self.game.update(self.input.frame(up=True), 1 / 60)
        first_vy = self.game.player.vy
        for _ in range(5):
            self.game.update(self.input.frame(up=True), 1 / 60)
        self.assertGreater(self.game.player.vy, first_vy)
        self.assertFalse(self.game.player.on_ground)

    def test_delivery_near_only_and_no_duplicate(self) -> None:
        self.game.update(self.input.frame(action_a=True), 1 / 60)
        self.assertEqual(self.game.stage.delivery_count, 0)
        self.game.player.x = self.game.stage.chimneys[0].x
        self.game.update(self.input.frame(), 1 / 60)
        self.game.update(self.input.frame(action_a=True), 1 / 60)
        self.assertEqual(self.game.stage.delivery_count, 1)
        self.assertEqual(len(self.game.gift_effects), 1)
        self.game.update(self.input.frame(), 1 / 60)
        self.game.update(self.input.frame(action_a=True), 1 / 60)
        self.assertEqual(self.game.stage.delivery_count, 1)

    def test_renderer_is_240_square_and_uses_assets(self) -> None:
        assets = AssetManager(ROOT / "assets")
        frame = Renderer(assets).render(self.game)
        self.assertEqual(frame.size, (240, 240))
        self.assertEqual(frame.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
