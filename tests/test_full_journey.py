import unittest

from santas_delivery.game import GameState
from santas_delivery.input import InputFrame

from helpers import DT, started_game


class FullJourneyTests(unittest.TestCase):
    def test_title_to_stage_two_all_clear(self) -> None:
        game = started_game()
        self.assertEqual(game.stage.delivery_goal, 10)
        for chimney in game.stage.chimneys:
            game.player.x = chimney.x
            self.assertTrue(game.try_delivery())
        game.player.x = game.stage.exit_x
        game.update(InputFrame(), DT)
        self.assertEqual(game.state, GameState.STAGE_CLEAR)
        game.state_timer = 0
        game.update(InputFrame(), DT)

        self.assertEqual(game.stage.id, 2)
        self.assertEqual(game.stage.delivery_goal, 10)
        for chimney in game.stage.chimneys[:-1]:
            game.player.x = chimney.x
            self.assertTrue(game.try_delivery())
        game.player.x = game.stage.boss_spec["warning_trigger_x"]
        game.update(InputFrame(), DT)
        self.assertEqual(game.state, GameState.WARNING)
        game.state_timer = 0
        game.update(InputFrame(), DT)
        self.assertEqual(game.state, GameState.BOSS_FIGHT)

        game.boss.hp = 1
        game.player.x = game.boss.x - 40
        game.player.facing = 1
        game.player.attack_cooldown = 0
        self.assertTrue(game.try_attack())
        for _ in range(30):
            game.update(InputFrame(), DT)
            if game.boss_defeated:
                break
        self.assertTrue(game.boss_defeated)
        final = game.stage.chimneys[-1]
        game.player.x = final.x
        self.assertTrue(game.try_delivery())
        self.assertEqual(game.state, GameState.ALL_CLEAR)
