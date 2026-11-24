import unittest

from santas_delivery.game import GameState
from santas_delivery.input import InputFrame

from helpers import DT, edge, started_game


class StageGoalTests(unittest.TestCase):
    def test_configured_goals(self) -> None:
        game = started_game()
        self.assertEqual(game.stage.delivery_goal, 10)
        game._load_stage(1)
        self.assertEqual(game.stage.normal_delivery_goal, 9)
        self.assertEqual(game.stage.delivery_goal, 10)

    def test_exit_requires_all_gifts_then_advances(self) -> None:
        game = started_game()
        game.player.x = game.stage.exit_x
        game.update(InputFrame(), DT)
        self.assertEqual(game.state, GameState.PLAYING)
        for chimney in game.stage.chimneys:
            game.player.x = chimney.x
            self.assertTrue(game.try_delivery())
        game.player.x = game.stage.exit_x
        game.update(InputFrame(), DT)
        self.assertEqual(game.state, GameState.STAGE_CLEAR)
        game.state_timer = 0
        game.update(InputFrame(), DT)
        self.assertEqual(game.stage.id, 2)
        self.assertEqual(game.state, GameState.PLAYING)

    def test_game_over_restart_resets_everything(self) -> None:
        game = started_game()
        game.player.x = game.stage.chimneys[0].x
        game.try_delivery()
        for _ in range(3):
            game.player.invulnerable = 0
            game.player.damage()
        game.update(InputFrame(), DT)
        self.assertEqual(game.state, GameState.GAME_OVER)
        game.update(edge("start"), DT)
        self.assertEqual(game.stage.id, 1)
        self.assertEqual(game.player.hp, 3)
        self.assertEqual(game.stage.delivery_count, 0)
