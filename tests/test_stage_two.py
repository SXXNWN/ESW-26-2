import unittest

from santas_delivery.input import InputFrame

from helpers import DT, started_game


class StageOneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = started_game()

    def test_stage_has_ranged_enemies(self) -> None:
        self.assertTrue(any(enemy.kind == "ranged" for enemy in self.game.enemies))

    def test_ranged_enemy_fires_real_projectile(self) -> None:
        ranged = next(enemy for enemy in self.game.enemies if enemy.kind == "ranged")
        self.game.player.x = 0
        self.assertGreater(abs(self.game.player.x - ranged.x), 230)
        ranged.shoot_timer = 0
        self.game.update(InputFrame(), DT)
        self.assertTrue(any(item.owner == "enemy" for item in self.game.projectiles))
