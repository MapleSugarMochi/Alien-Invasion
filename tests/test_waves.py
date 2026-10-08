import unittest
from collections import Counter

from pygame import Vector2

from entities import Enemy, Pickup
from game import Game
from settings import DIFFICULTIES, LEVEL_CONFIGS
from waves import WaveController


class WaveTests(unittest.TestCase):
    def test_all_waves_leave_naturally_with_caps(self):
        for difficulty in DIFFICULTIES.values():
            for level in (2, 3):
                with self.subTest(difficulty=difficulty.id, level=level):
                    self.check_natural_waves(difficulty, level)

    def check_natural_waves(self, difficulty, level):
        counts, total = Counter(), 0
        now = 0.0
        for number in range(1, 13):
            wave = WaveController(number, now, LEVEL_CONFIGS[level].waves)
            active = []
            first = wave.update(now, 0, difficulty, total + 1)
            self.assertIsNotNone(first)
            active.append(first)
            total += 1
            counts[first.kind] += 1
            # 简单上限为 3，慢速侧面重型入场和 10 秒停留会拉长波次。
            deadline = now + 120
            while wave.queue or active:
                now += 1 / 60
                for enemy in active:
                    enemy.update(1 / 60, now, Vector2(640, 650))
                active = [e for e in active if not e.gone]
                enemy = wave.update(now, len(active), difficulty, total + 1)
                if enemy:
                    active.append(enemy)
                    total += 1
                    counts[enemy.kind] += 1
                self.assertLessEqual(len(active), difficulty.enemy_cap)
                self.assertLess(now, deadline, (difficulty.id, number))
            now += 3
        self.assertEqual(total, 142 if level == 3 else 118)
        self.assertEqual(counts, {"scout": 75, "shooter": 43, "heavy": 24} if level == 3
                         else {"scout": 62, "shooter": 36, "heavy": 20})

    def test_full_cap_keeps_queue_and_resets_interval(self):
        wave = WaveController(1, 0)
        easy = DIFFICULTIES["easy"]
        self.assertIsNone(wave.update(10, 3, easy, 1))
        self.assertEqual(len(wave.queue), 8)
        self.assertIsNotNone(wave.update(10, 2, easy, 1))
        self.assertIsNone(wave.update(10, 2, easy, 2))
        self.assertEqual(len(wave.queue), 7)

    def test_heavy_pressure_positions_match_wave_plan(self):
        for number, expected in ((8, [480, 800]), (12, [160, 480, 800, 1120])):
            wave = WaveController(number, 0)
            positions = []
            now = 0
            while wave.queue:
                enemy = wave.update(now, 0, DIFFICULTIES["standard"], len(positions) + 1)
                if enemy.kind == "heavy":
                    positions.append(enemy.pos.x)
                now += wave.interval
            self.assertEqual(positions, expected)

    def test_drop_boundaries_full_health_and_expiry(self):
        game = Game(seed=1)
        game.update(6.999)
        self.assertFalse(any(e["event"] == "drop" for e in game.journal))
        game.update(.001)
        self.assertEqual(len([e for e in game.journal if e["event"] == "drop"]), 1)
        self.assertAlmostEqual(game.pickups[0].born_at, 7)
        game.update(7)
        self.assertEqual(len([e for e in game.journal if e["event"] == "drop"]), 2)
        game.phase = "boss_ready"
        game.enemies.clear()
        game.meteors.clear()
        game.enemy_bullets.clear()
        game.player.hp = 100
        pickup = Pickup(1000, game.player.pos.copy(), game.time)
        game.pickups = [pickup]
        game.update(.01)
        self.assertFalse(pickup.consumed)
        game.player.hp = 90
        game.update(.01)
        self.assertTrue(pickup.consumed)
        self.assertEqual(game.player.hp, 100)
        self.assertTrue(Pickup(1, Vector2(), 0).expired(10))

    def test_boss_clear_cancels_reserved_meteor(self):
        game = Game()
        game.wave = WaveController(12, 0)
        game.wave.queue.clear()
        game.meteor_warning = (1, 500, 22)
        game.timed_events()
        self.assertIsNone(game.meteor_warning)
        self.assertEqual(game.phase, "boss_warning")
        game.update(3)
        self.assertFalse(game.meteors)

    def test_shooter_and_heavy_leave_after_fixed_hold(self):
        for kind, duration in (("shooter", 8), ("heavy", 10)):
            enemy = Enemy.create(1, kind, (500, 150 if kind == "heavy" else 180),
                                 DIFFICULTIES["standard"], 0)
            enemy.update(.01, .01, Vector2(640, 500))
            self.assertEqual(enemy.hold_until, duration + .01)
            enemy.update(.01, duration + .02, Vector2(640, 500))
            self.assertEqual(enemy.mode, "leaving")
