import unittest
from pygame import Vector2

from entities import Boss, Enemy, Meteor, Pickup
from game import Game
from weapons import Projectile, SupportController
import pygame
from render import Renderer
from weapons import SupportRound


class SupportTests(unittest.TestCase):
    def test_support_render_at_fractional_launch_boundary(self):
        pygame.font.init()
        game = Game()
        game.enemies = [Enemy(1, Vector2(200, 200))]
        game.time = 2.8
        game.support.rounds = [SupportRound(1, 2.4, [1], launched=True)]
        Renderer().draw(pygame.Surface((1280, 720)), game)

    def test_actual_damage_and_contact_rewards(self):
        game = Game()
        enemy = Enemy(1, Vector2(200, 200))
        game.apply_damage(enemy, 60, "missile")
        self.assertEqual((game.energy_units, game.score, game.kills), (40, 100, 1))
        game.apply_damage(enemy, 60, "missile")
        self.assertEqual(game.energy_units, 40)
        game.apply_damage(Meteor(2, Vector2()), 60, "missile")
        self.assertEqual(game.energy_units, 40)
        game.apply_damage(Enemy(3, Vector2()), 20, "contact")
        self.assertEqual(game.energy_units, 60)

    def test_zero_one_two_three_targets_and_five_rounds(self):
        for count in range(5):
            support = SupportController()
            candidates = [Enemy(i + 1, Vector2(100 + i * 80, 200)) for i in range(count)]
            support.start(0)
            events = []
            for now in (0, .4, .65, 1.5, 1.9, 2.15, 3, 3.4, 3.65, 4.5, 4.9, 5.15, 6, 6.4, 6.65):
                events += support.update(now, candidates, Vector2(300, 200))
            rounds = [e for e in events if e[0] == "round"]
            hits = [e for e in events if e[0] == "hit"]
            self.assertEqual(len(rounds), 5)
            self.assertEqual(len(hits), 5)
            self.assertTrue(all(len(e[2]) == min(count, 3) and len(set(e[2])) == len(e[2]) for e in hits))
            self.assertTrue(support.expire(7.5))
            self.assertFalse(support.update(9, candidates, Vector2()))
            self.assertEqual(support.round_count, 5)

    def test_replacement_is_unique_and_flight_invalidation_cancels(self):
        support = SupportController()
        candidates = [Enemy(i + 1, Vector2(100 + i * 50, 200)) for i in range(5)]
        support.start(0)
        support.update(0, candidates, Vector2(100, 200))
        candidates[0].hp = 0
        candidates[1].pos.y = 800
        launch = support.update(.4, candidates, Vector2(100, 200))
        self.assertEqual(set(launch[0][2]), {3, 4, 5})
        candidates[2].hp = 0
        hit = support.update(.65, candidates, Vector2(100, 200))
        self.assertEqual(set(hit[0][2]), {4, 5})

    def test_full_boss_loses_half_for_all_difficulties(self):
        for difficulty, damage in (("easy", 192), ("standard", 240), ("hard", 300)):
            game = Game(difficulty)
            game.phase = "boss_fight"
            game.boss = Boss(1, game.difficulty)
            game.boss.entering = False
            game.boss.pos.update(640, 180)
            game.boss.previous = game.boss.pos.copy()
            game.boss.reset_schedule(0)
            game.energy_units = 1000
            self.assertTrue(game.try_support())
            game.update(7.5)
            self.assertEqual(game.boss.max_hp // 10, damage)
            self.assertEqual(game.boss.hp, game.boss.max_hp // 2)
            self.assertFalse(game.support.active)
            self.assertEqual(game.energy_units, 0)
            self.assertEqual(len([e for e in game.journal if e["event"] == "support_round"]), 5)

    def test_level_three_support_scales_with_increased_boss_health(self):
        for difficulty, damage in (("easy", 268), ("standard", 336), ("hard", 420)):
            with self.subTest(difficulty=difficulty):
                game = Game(difficulty, level=3)
                game.phase = "boss_warning"
                game.timed_events()
                game.phase = "boss_fight"
                game.boss.entering = False
                game.boss.pos.update(640, 180)
                game.boss.previous = game.boss.pos.copy()
                game.boss.reset_schedule(0)
                game.energy_units = 1000
                self.assertTrue(game.try_support())
                game.update(7.5)
                self.assertEqual(game.boss.max_hp // 10, damage)
                self.assertEqual(game.boss.hp, game.boss.max_hp - damage * 5)
                self.assertFalse(game.support.active)
                self.assertEqual(game.energy_units, 0)
                self.assertEqual(len([e for e in game.journal if e["event"] == "support_hit"]), 5)

    def test_support_suppresses_energy_but_not_pickup_or_stats(self):
        game = Game()
        game.energy_units = 999
        self.assertFalse(game.try_support())
        self.assertEqual(game.energy_units, 999)
        game.energy_units = 1000
        self.assertTrue(game.try_support())
        self.assertFalse(game.try_support())
        game.apply_damage(Enemy(1, Vector2()), 20, "bullet")
        self.assertEqual((game.energy_units, game.score, game.kills), (0, 100, 1))
        game.player.hp = 75
        game.collect(Pickup(1, Vector2(), 0))
        game.collect(Pickup(2, Vector2(), 0, "arc"))
        self.assertEqual((game.player.hp, game.weapons.charges["arc"]), (100, 1))
        game.pause()
        game.update(30)
        self.assertEqual((game.time, game.support.round_count), (0, 0))
        game.resume()
        game.update(.01)
        self.assertEqual(game.support.round_count, 1)
        old_support = game.support
        game.finish("defeat")
        self.assertFalse(old_support.active)

    def test_end_timestamp_clears_before_new_damage(self):
        game = Game()
        game.phase = "boss_fight"
        game.energy_units = 1000
        game.try_support()
        game.time = 7.49
        game.support.round_count = 5
        enemy = Enemy(1, Vector2(200, 200))
        game.enemies = [enemy]
        game.projectiles = [Projectile(enemy.pos.copy(), Vector2(), 10)]
        game.update(.01)
        self.assertFalse(game.support.active)
        self.assertEqual(game.energy_units, 10)

    def test_quit_cancels_all_support_resources(self):
        for via_event in (False, True):
            game = Game()
            game.energy_units = 1000
            game.try_support()
            game.pickups.append(Pickup(1, Vector2(), 0, "arc"))
            game.commands.append("arc")
            if via_event:
                game.handle_events([pygame.event.Event(pygame.QUIT)])
            else:
                game.menu_action("quit")
            self.assertFalse(game.running)
            self.assertFalse(game.support.active)
            self.assertFalse(game.pickups)
            self.assertFalse(game.commands)
            self.assertEqual(game.energy_units, 0)

    def test_pause_freezes_special_support_and_boss_deadlines(self):
        game = Game()
        game.phase = "boss_fight"
        game.boss = Boss(1, game.difficulty)
        game.boss.entering = False
        game.boss.pos.update(640, 180)
        game.boss.reset_schedule(0)
        game.weapons.charges["missile"] = 3
        game.weapons.try_activate("missile", 0)
        game.energy_units = 1000
        game.try_support()
        game.update(.3)
        game.pause()
        before = (game.time, game.weapons.active_until, game.weapons.ready_at,
                  game.support.end_at, game.support.round_count, game.boss.next_round,
                  game.next_drop, game.next_meteor, game.boss.pos.copy())
        game.update(60)
        after = (game.time, game.weapons.active_until, game.weapons.ready_at,
                 game.support.end_at, game.support.round_count, game.boss.next_round,
                 game.next_drop, game.next_meteor, game.boss.pos.copy())
        self.assertEqual(before, after)
