import unittest

from pygame import Vector2

from entities import Boss
from game import Game
from weapons import Projectile


class BossTests(unittest.TestCase):
    def scene(self):
        game = Game(level=2)
        game.phase = "boss_fight"
        game.boss = Boss(999, game.difficulty)
        game.boss.entering = False
        game.boss.pos.update(640, 180)
        game.boss.previous = game.boss.pos.copy()
        game.boss.reset_schedule(0)
        return game

    def test_entry_and_health_boundaries(self):
        game = Game(level=2)
        boss = Boss(1, game.difficulty)
        self.assertEqual(game.apply_damage(boss, 100, "bullet"), 0)
        self.assertEqual(boss.update(1, 1, game.player.pos), [])
        self.assertTrue(boss.entering)
        boss.update(1, 2, game.player.pos)
        self.assertFalse(boss.entering)
        for hp, expected in ((1601, 1), (1600, 2), (800, 2), (799, 3)):
            boss.hp = hp
            self.assertEqual(boss.health_phase(), expected)

    def test_transition_cancels_burst_and_does_not_extend(self):
        game = self.scene()
        boss = game.boss
        boss.burst = [0, .05, .1]
        game.apply_damage(boss, 801, "bullet")
        self.assertEqual(boss.burst, [])
        self.assertEqual(boss.transition_until, 1)
        before = boss.pos.copy()
        boss.update(.5, .5, Vector2(100, 400))
        self.assertEqual(boss.pos, before)
        game.time = .5
        game.apply_damage(boss, 1000, "bullet")
        self.assertEqual(boss.transition_until, 1)
        boss.update(.5, 1, game.player.pos)
        self.assertEqual(boss.phase, 3)
        self.assertEqual(len(boss.update(.9, 1.9, game.player.pos)), 7)
        self.assertEqual(len(boss.update(.9, 2.8, game.player.pos)), 1)
        self.assertEqual(len(boss.update(.05, 2.85, Vector2(1200, 600))), 1)
        self.assertEqual(len(boss.update(.05, 2.9, Vector2(100, 600))), 1)

    def test_boss_contact_does_not_damage_boss(self):
        game = self.scene()
        game.player.pos = game.boss.pos.copy()
        game.contacts()
        self.assertEqual(game.player.hp, 80)
        self.assertEqual(game.boss.hp, 2400)

    def test_double_death_is_defeat_in_both_orders(self):
        for order in ("boss_first", "player_first"):
            game = self.scene()
            game.boss.hp, game.player.hp = 10, 10
            if order == "boss_first":
                game.apply_damage(game.boss, 10, "bullet")
                game.damage_player(10)
            else:
                game.damage_player(10)
                game.apply_damage(game.boss, 10, "bullet")
            game.update(0)
            self.assertEqual(game.state, "defeat")

    def test_later_substep_can_defeat_after_boss_kill(self):
        game = self.scene()
        game.player.hp = 10
        game.boss.hp = 10
        game.projectiles = [Projectile(game.boss.pos.copy(), Vector2(), 10)]
        game.enemy_bullets = [Projectile(game.player.pos + Vector2(0, -30), Vector2(0, 900),
                                         10, 4, "enemy", float("inf"))]
        game.update(.05)
        self.assertEqual((game.boss.hp, game.player.hp, game.state), (0, 0, "defeat"))

    def test_restart_resets_everything(self):
        game = self.scene()
        game.finish("victory")
        game.restart()
        self.assertEqual((game.time, game.player.hp, game.score, game.kills, game.next_drop), (0, 100, 0, 0, 7))
        self.assertEqual(game.wave.number, 1)
        self.assertIsNone(game.boss)
        self.assertFalse(game.projectiles)
