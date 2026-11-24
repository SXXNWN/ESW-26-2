import unittest

from santas_delivery.game import GameState
from santas_delivery.input import InputFrame

from helpers import DT, started_game


class BossProgressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = started_game()
        self.game._load_stage(1)

    def test_missing_gifts_block_boss_without_softlock(self) -> None:
        trigger = self.game.stage.boss_spec["warning_trigger_x"]
        self.game.player.x = trigger
        self.game.update(InputFrame(), DT)
        self.assertEqual(self.game.state, GameState.PLAYING)
        self.assertLess(self.game.player.x, trigger)
        self.assertIn("9 GIFTS", self.game.message)

    def test_warning_boss_damage_gate_and_all_clear(self) -> None:
        for chimney in self.game.stage.chimneys[:-1]:
            self.game.player.x = chimney.x
            self.assertTrue(self.game.try_delivery())
        self.game.player.x = self.game.stage.boss_spec["warning_trigger_x"]
        self.game.update(InputFrame(), DT)
        self.assertEqual(self.game.state, GameState.WARNING)
        self.game.state_timer = 0
        self.game.update(InputFrame(), DT)
        self.assertEqual(self.game.state, GameState.BOSS_FIGHT)
        self.assertTrue(self.game.boss.active)

        self.game.player.x = self.game.boss.x - 40
        for _ in range(10):
            self.game.player.attack_cooldown = 0
            self.assertTrue(self.game.try_attack())
            old_hp = self.game.boss.hp
            for _ in range(20):
                self.game.update(InputFrame(), DT)
                if self.game.boss.hp < old_hp:
                    break
            self.assertLess(self.game.boss.hp, old_hp)
        self.assertTrue(self.game.boss_defeated)
        self.assertTrue(self.game.boss.defeated)

        final = self.game.stage.chimneys[-1]
        self.game.player.x = final.x
        self.assertTrue(self.game.try_delivery())
        self.assertEqual(self.game.state, GameState.ALL_CLEAR)
