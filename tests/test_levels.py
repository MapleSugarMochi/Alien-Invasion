import unittest

import pygame

from game import Game
from settings import DIFFICULTIES, LEVELS


def click_button(game, action):
    position = next(rect.center for name, _, rect in game.buttons() if name == action)
    game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position),
                        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=position)])


class LevelTests(unittest.TestCase):
    def test_three_mouse_entries_start_with_chosen_difficulty_and_fresh_input(self):
        for language in ("en", "zh-CN"):
            for difficulty in DIFFICULTIES:
                for level in LEVELS:
                    with self.subTest(language=language, difficulty=difficulty, level=level):
                        game = Game(menu=True, language=language)
                        click_button(game, "level_select")
                        entries = [action for action, _, _ in game.buttons() if action.startswith("level_")]
                        self.assertEqual(entries, ["level_1", "level_2", "level_3"])
                        click_button(game, difficulty)
                        click_button(game, f"level_{level}")
                        self.assertEqual((game.state, game.level, game.difficulty.id, game.wave.number),
                                         ("playing", level, difficulty, 1))
                        self.assertFalse(game.input.fire)
                        self.assertFalse(game.input.keys)
                        self.assertEqual(game.journal, [{"time": 0.0, "event": "session_start",
                                                       "difficulty": difficulty, "level": level}])

    def test_level_keyboard_shortcuts_return_and_repeat(self):
        for level, key in zip(LEVELS, (pygame.K_1, pygame.K_2, pygame.K_3)):
            with self.subTest(level=level):
                game = Game(menu=True)
                game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])
                game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=key, repeat=True)])
                self.assertEqual(game.state, "level_select")
                game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)])
                self.assertEqual(game.state, "main_menu")
                click_button(game, "level_select")
                game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=key)])
                self.assertEqual((game.state, game.level), ("playing", level))
                game.pause()
                click_button(game, "restart")
                game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])
                self.assertEqual((game.state, game.level), ("playing", level))

    def test_restart_and_results_return_to_levels_and_clear_old_battle(self):
        for state in ("paused", "victory", "defeat"):
            with self.subTest(state=state):
                game = Game(menu=True)
                click_button(game, "level_select")
                click_button(game, "hard")
                click_button(game, "level_3")
                game.preferences.bindings["move_right"] = pygame.K_RIGHT
                game.language = "zh-CN"
                game.sfx_volume = .2
                preferences = game.preferences
                game.energy_units = 1000
                game.try_support()
                game.weapons.charges["missile"] = 3
                game.input.fire = True
                game.update(.5)
                game.score, game.kills, game.player.hp = 700, 7, 20
                game.state = state
                click_button(game, "restart")
                self.assertEqual((game.state, game.level, game.selected_difficulty),
                                 ("level_select", 3, "hard"))
                self.assertEqual((game.time, game.score, game.kills, game.player.hp, game.energy_units),
                                 (0, 0, 0, 100, 0))
                self.assertFalse(game.enemies or game.projectiles or game.pickups or game.commands)
                self.assertFalse(game.support.active or game.input.fire or any(game.weapons.charges.values()))
                self.assertIs(game.preferences, preferences)
                click_button(game, "easy")
                click_button(game, "level_2")
                self.assertEqual((game.level, game.difficulty.id, game.language, game.sfx_volume),
                                 (2, "easy", "zh-CN", .2))
                self.assertEqual(game.preferences.bindings["move_right"], pygame.K_RIGHT)

    def test_settings_return_preserves_level_and_difficulty_selection(self):
        game = Game(menu=True, level=2)
        click_button(game, "level_select")
        click_button(game, "hard")
        game.open_settings()
        game.menu_action("language_zh-CN")
        game.update(5)
        game.menu_action("settings_back")
        self.assertEqual((game.state, game.level, game.selected_difficulty, game.time),
                         ("level_select", 2, "hard", 0))
        click_button(game, "level_2")
        self.assertEqual((game.level, game.difficulty.id, game.language), (2, "hard", "zh-CN"))

    def test_level_actions_cannot_change_active_battle_or_settings(self):
        for state in ("main_menu", "playing", "paused", "settings", "victory", "defeat"):
            with self.subTest(state=state):
                game = Game(level=2)
                game.state = state
                for action in ("setup", "start", "level_1", "level_3", "level_4"):
                    game.menu_action(action)
                self.assertEqual((game.state, game.level, game.time), (state, 2, 0))
        with self.assertRaises(ValueError):
            Game(level=4)

    def test_identical_seed_and_inputs_produce_identical_content_for_all_levels(self):
        runs = []
        for level in LEVELS:
            game = Game(menu=True)
            click_button(game, "level_select")
            click_button(game, f"level_{level}")
            game.rng.seed(5)
            game.input.fire = True
            for _ in range(600):
                game.update(1 / 60)
            runs.append((game.state, game.time, game.player.hp, game.score,
                         game.wave.number, game.phase, game.journal[1:]))
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(runs[1], runs[2])
