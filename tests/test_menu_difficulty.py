import unittest

import pygame
from pygame import Vector2

from entities import Enemy
from game import Game


class MenuDifficultyTests(unittest.TestCase):
    def test_menu_buttons_restart_and_change_difficulty(self):
        game = Game(menu=True, level=2)
        game.menu_action("level_select")
        game.menu_action("hard")
        game.menu_action("level_2")
        self.assertEqual(game.difficulty.id, "hard")
        game.update(1)
        game.pause()
        game.menu_action("restart")
        self.assertEqual((game.difficulty.id, game.player.hp, game.time), ("hard", 100, 0))
        self.assertEqual(game.state, "level_select")
        game.menu_action("menu")
        self.assertEqual(game.state, "main_menu")
        self.assertFalse(game.enemies)
        game.menu_action("level_select")
        game.menu_action("easy")
        game.menu_action("level_2")
        self.assertEqual(game.difficulty.hp(50), 40)
        game.menu_action("quit")
        self.assertFalse(game.running)

    def test_difficulty_changes_actual_enemy_motion_and_shooting(self):
        results = []
        for difficulty in ("easy", "standard", "hard"):
            game = Game(difficulty, level=2)
            enemy = Enemy.create(1, "shooter", (640, 180), game.difficulty, 0)
            enemy.begin_hold(0)
            before = enemy.pos.copy()
            emitted = []
            now = 0
            for _ in range(120):
                now += 1 / 60
                emitted.extend(enemy.update(1 / 60, now, Vector2(640, 650)))
            results.append((enemy.hp, enemy.pos.x - before.x, len(emitted),
                            enemy.bullet_speed, enemy.bullet_damage))
        self.assertEqual([r[0] for r in results], [40, 50, 62])
        self.assertAlmostEqual(results[0][1], 176)
        self.assertAlmostEqual(results[1][1], 220)
        self.assertAlmostEqual(results[2][1], 264)
        self.assertEqual([r[2] for r in results], [1, 2, 2])
        self.assertEqual([r[3] for r in results], [187.5, 250, 312.5])
        self.assertEqual([r[4] for r in results], [7, 10, 12])

    def test_mouse_menu_hit_and_focus_does_not_resume(self):
        game = Game(menu=True, level=2)
        game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 400))])
        self.assertEqual(game.state, "level_select")
        game.menu_action("hard")
        game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3),
                            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])
        self.assertEqual(game.difficulty.id, "hard")
        self.assertEqual(game.level, 3)
        self.assertFalse(game.input.fire)
        game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST),
                            pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        self.assertEqual(game.state, "paused")
