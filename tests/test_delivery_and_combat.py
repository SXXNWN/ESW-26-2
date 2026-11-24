import unittest

from santas_delivery.entities import Projectile
from santas_delivery.game import GameState
from santas_delivery.input import InputFrame

from helpers import DT, started_game


class DeliveryCombatTests(unittest.TestCase):
    def test_final_chimney_is_locked(self) -> None:
        game = started_game()
        game._load_stage(1)
        final = game.stage.chimneys[-1]
        game.player.x = final.x
        self.assertFalse(game.try_delivery())
        self.assertFalse(final.delivered)
        self.assertIn("LOCKED", game.message)

    def test_attack_direction_cooldown_and_enemy_damage(self) -> None:
        game = started_game()
        enemy = game.enemies[0]
        enemy.hp = 1
        game.enemies = [enemy]
        game.player.x = enemy.x - 48
        game.player.facing = 1
        self.assertTrue(game.try_attack())
        self.assertGreater(game.projectiles[0].vx, 0)
        self.assertFalse(game.try_attack())
        for _ in range(30):
            game.update(InputFrame(), DT)
            if not enemy.alive:
                break
        self.assertFalse(enemy.alive)

    def test_projectiles_expire_outside_world(self) -> None:
        game = started_game()
        game.projectiles.append(Projectile(game.stage.world_width + 40, 100, 100, "player"))
        game.update(InputFrame(), DT)
        self.assertEqual(game.projectiles, [])

    def test_held_attack_repeats_only_at_cooldown_rate(self) -> None:
        game = started_game()
        game.enemies = []
        for _ in range(60):
            game.update(InputFrame(action_b=True), DT)
        self.assertGreaterEqual(len(game.projectiles), 2)
        self.assertLessEqual(len(game.projectiles), 3)

    def test_damage_invulnerability_and_game_over(self) -> None:
        game = started_game()
        self.assertTrue(game.player.damage())
        self.assertEqual(game.player.hp, 2)
        self.assertFalse(game.player.damage())
        self.assertEqual(game.player.hp, 2)
        game.player.invulnerable = 0
        game.player.damage()
        game.player.invulnerable = 0
        game.player.damage()
        game.update(InputFrame(), DT)
        self.assertEqual(game.state, GameState.GAME_OVER)

    def test_crouching_avoids_high_ranged_shot(self) -> None:
        game = started_game()
        game.player.crouching = False
        shot = Projectile(game.player.x + 8, game.player.y + 4, 0, "enemy")
        self.assertTrue(shot.hitbox.intersects(game.player.hitbox))
        game.player.crouching = True
        self.assertFalse(shot.hitbox.intersects(game.player.hitbox))
