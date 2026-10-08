import unittest

import pygame
from pygame import Vector2

from entities import Enemy, Meteor
from game import Game
from geometry import circle_hit, moving_hit
from weapons import Projectile


class RuleTests(unittest.TestCase):
    def scene(self):
        game = Game()
        game.enemies.clear()
        game.meteors.clear()
        return game

    def test_high_speed_first_hit_and_range(self):
        game = self.scene()
        first, second = Enemy(1, Vector2(150, 200)), Enemy(2, Vector2(250, 200))
        shot = Projectile(Vector2(100, 200), Vector2(900, 0))
        game.resolve_projectile(shot, .3, [second, first])
        self.assertEqual((first.hp, second.hp), (10, 20))
        self.assertFalse(shot.alive)
        out_of_range = Projectile(Vector2(100, 200), Vector2(900, 0), remaining_range=10)
        game.resolve_projectile(out_of_range, .3, [first])
        self.assertEqual(first.hp, 10)
        self.assertFalse(out_of_range.alive)

    def test_relative_motion_overlap_and_zero_length(self):
        self.assertIsNotNone(moving_hit(Vector2(0, 100), Vector2(100, 100),
                                        Vector2(50, 0), Vector2(50, 200), 10))
        self.assertEqual(circle_hit(Vector2(), Vector2(), Vector2(), 1), 0)
        self.assertIsNone(circle_hit(Vector2(), Vector2(), Vector2(20, 0), 1))

    def test_offscreen_muzzle_is_recycled_before_collision(self):
        game = self.scene()
        enemy = Enemy(1, Vector2(-16, 200))
        shot = Projectile(Vector2(-1, 200), Vector2(-900, 0))
        game.resolve_projectile(shot, .1, [enemy])
        self.assertEqual(enemy.hp, 20)
        self.assertFalse(shot.alive)

    def test_hud_aim_is_clamped_for_heading_but_never_fires(self):
        game = self.scene()
        game.input.aim.update(100, 5)
        game.input.fire = True
        game.update(.01)
        expected = (Vector2(100, 64) - game.player.pos).normalize()
        self.assertLess(game.player.direction.distance_to(expected), 1e-8)
        self.assertIsNone(game.weapons.last_shot_at)

    def test_enemy_bullet_absorbed_by_meteor(self):
        game = self.scene()
        game.player.pos.update(300, 200)
        game.player.previous = game.player.pos.copy()
        meteor = Meteor(2, Vector2(200, 200))
        shot = Projectile(Vector2(100, 200), Vector2(900, 0), source="enemy")
        game.resolve_projectile(shot, .4, [game.player, meteor])
        self.assertEqual((game.player.hp, meteor.hp), (100, 40))
        self.assertFalse(shot.alive)

    def test_contact_invulnerability_and_death_once(self):
        game = self.scene()
        first = Enemy(1, game.player.pos.copy())
        game.enemies = [first]
        game.contacts()
        self.assertEqual((game.player.hp, first.hp, game.kills, game.score), (80, 0, 1, 100))
        second = Enemy(2, game.player.pos.copy())
        game.enemies = [second]
        game.contacts()
        self.assertEqual((game.player.hp, second.hp), (80, 20))
        game.finalize_kill(first)
        self.assertEqual(game.kills, 1)
        game.time = .8
        game.enemies = [Enemy(3, game.player.pos.copy())]
        game.contacts()
        self.assertEqual(game.player.hp, 60)

    def test_shared_cooldown_release_and_hud(self):
        game = self.scene()
        game.input.fire = True
        game.update(.119)
        self.assertEqual(game.weapons.last_shot_at, 0)
        game.input.fire = False
        game.update(.001)
        self.assertEqual(game.weapons.last_shot_at, 0)
        game.input.fire = True
        game.update(.001)
        self.assertAlmostEqual(game.weapons.last_shot_at, .12)
        game.input.aim.update(500, 20)
        last = game.weapons.last_shot_at
        game.update(.5)
        self.assertEqual(game.weapons.last_shot_at, last)

    def test_focus_pause_and_fresh_mouse_press(self):
        game = self.scene()
        game.input.fire = True
        game.input.keys.add(pygame.K_d)
        game.player.invulnerable_until = 1
        game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        before = game.player.pos.copy()
        game.update(20)
        self.assertEqual((game.time, game.player.pos), (0, before))
        game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.assertEqual(game.state, "paused")
        game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)])
        game.update(.1)
        self.assertFalse(game.input.fire)
        self.assertIsNone(game.weapons.last_shot_at)


if __name__ == "__main__":
    unittest.main()
