import json
from pathlib import Path
import tempfile
import unittest

import pygame
from pygame import Vector2

from game import Game
from preferences import DEFAULT_BINDINGS, Preferences


def click(game, position):
    game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position)])


def press(game, key, **attributes):
    game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=key, **attributes)])


class SettingsTests(unittest.TestCase):
    def settings_game(self):
        game = Game(menu=True, level=2)
        game.menu_action("settings")
        return game

    def rebind(self, game, action, key):
        rect = next(rect for name, _, _, rect in game.control_rows() if name == action)
        click(game, rect.center)
        self.assertEqual(game.editing_binding, action)
        press(game, key)
        self.assertIsNone(game.editing_binding)
        self.assertEqual(game.preferences.bindings[action], key)

    def test_capture_any_key_precedes_menu_navigation_and_repeat_is_ignored(self):
        for key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_F1, pygame.K_LCTRL, pygame.K_SPACE):
            with self.subTest(key=key):
                game = self.settings_game()
                self.rebind(game, "move_up", key)
                self.assertEqual((game.state, game.language), ("settings", "en"))
        game = self.settings_game()
        rect = game.control_rows()[0][3]
        click(game, rect.center)
        press(game, pygame.K_SPACE, repeat=True)
        self.assertEqual(game.editing_binding, "move_up")
        click(game, (20, 20))
        self.assertIsNone(game.editing_binding)

    def test_remapped_motion_and_pause_replace_old_keys_and_survive_restart(self):
        game = self.settings_game()
        self.rebind(game, "move_right", pygame.K_RIGHT)
        self.rebind(game, "pause", pygame.K_p)
        game.menu_action("settings_back")
        game.menu_action("level_select")
        game.menu_action("level_2")
        press(game, pygame.K_d)
        self.assertEqual(game.input.movement, Vector2())
        press(game, pygame.K_RIGHT)
        self.assertEqual(game.input.movement, Vector2(1, 0))
        press(game, pygame.K_ESCAPE)
        self.assertEqual(game.state, "playing")
        press(game, pygame.K_p)
        self.assertEqual(game.state, "paused")
        game.menu_action("settings")
        game.update(5)
        self.assertEqual(game.time, 0)
        game.menu_action("settings_back")
        self.assertEqual(game.state, "paused")
        press(game, pygame.K_p)
        self.assertEqual(game.state, "playing")
        game.restart()
        self.assertEqual(game.state, "level_select")
        self.assertEqual(game.preferences.bindings["move_right"], pygame.K_RIGHT)

    def test_conflicts_trigger_all_actions_without_exchanging_keys(self):
        game = self.settings_game()
        for action in ("move_right", "move_up", "missile", "arc", "support"):
            self.rebind(game, action, pygame.K_z)
        self.assertEqual(game.preferences.conflicts(), {"move_right", "move_up", "missile", "arc", "support"})
        self.assertEqual(game.preferences.bindings["move_left"], pygame.K_a)
        game.menu_action("settings_back")
        game.menu_action("level_select")
        game.menu_action("level_2")
        game.weapons.charges.update(missile=3, arc=3)
        game.energy_units = 1000
        press(game, pygame.K_z)
        self.assertEqual(game.input.movement, Vector2(1, -1))
        self.assertEqual(game.commands, ["missile", "arc", "support"])
        press(game, pygame.K_z, repeat=True)
        self.assertEqual(len(game.commands), 3)
        game.update(.1)
        self.assertTrue(game.support.active)
        self.assertEqual(game.weapons.active, "missile")
        self.assertEqual(game.weapons.charges["arc"], 3)
        game.handle_events([pygame.event.Event(pygame.KEYUP, key=pygame.K_z)])
        self.assertEqual(game.input.movement, Vector2())

    def test_pause_shared_with_weapon_activates_weapon_before_freezing(self):
        game = Game(level=2)
        game.preferences.bindings["missile"] = pygame.K_ESCAPE
        game.weapons.charges["missile"] = 3
        press(game, pygame.K_ESCAPE)
        self.assertEqual((game.state, game.weapons.active), ("paused", "missile"))
        game.update(1)
        self.assertEqual(game.time, 0)

    def test_reset_keys_only_preserves_language_volumes_and_clears_conflicts(self):
        game = self.settings_game()
        game.language = "zh-CN"
        game.sfx_volume, game.music_volume = .2, .8
        self.rebind(game, "move_up", pygame.K_q)
        self.assertTrue(game.preferences.conflicts())
        reset = next(rect for action, _, rect in game.buttons() if action == "reset_keys")
        click(game, reset.center)
        self.assertEqual(game.preferences.bindings, DEFAULT_BINDINGS)
        self.assertIs(game.input.bindings, game.preferences.bindings)
        self.assertEqual((game.language, game.sfx_volume, game.music_volume), ("zh-CN", .2, .8))
        self.assertFalse(game.preferences.conflicts())
        self.assertIsNone(game.editing_binding)

    def test_drag_sliders_clamps_saves_and_focus_loss_stops_drag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            game = Game(menu=True, preferences=Preferences.load(path))
            game.menu_action("settings")
            rect = game.sliders()[0][1]
            click(game, (rect.left + rect.width // 2, rect.centery))
            self.assertEqual(game.sfx_volume, .5)
            game.handle_events([pygame.event.Event(pygame.MOUSEMOTION, pos=(rect.right + 200, 300))])
            self.assertEqual(game.sfx_volume, 1)
            game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(rect.left - 100, 300))])
            self.assertEqual(game.sfx_volume, 0)
            self.assertEqual(Preferences.load(path).sfx_volume, 0)
            self.assertEqual(game.music_volume, .35)
            click(game, rect.center)
            game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
            self.assertIsNone(game.dragging_slider)
            self.assertEqual(Preferences.load(path).sfx_volume, .5)

    def test_difficulty_is_only_selected_before_each_new_battle(self):
        game = Game("hard", level=2)
        original = game.difficulty
        game.pause()
        game.menu_action("settings")
        self.assertFalse(any(action in ("easy", "standard", "hard") for action, _, _ in game.buttons()))
        game.menu_action("easy")
        game.menu_action("level_2")
        self.assertEqual(game.state, "settings")
        self.assertIs(game.difficulty, original)
        self.assertEqual(game.selected_difficulty, "hard")
        game.menu_action("settings_back")
        game.menu_action("restart")
        self.assertEqual(game.state, "level_select")
        game.menu_action("easy")
        game.menu_action("level_2")
        self.assertEqual((game.state, game.difficulty.id), ("playing", "easy"))
        game.finish("victory")
        press(game, pygame.K_r)
        self.assertEqual(game.state, "level_select")

    def test_fixed_mouse_rows_cannot_be_rebound(self):
        game = self.settings_game()
        for action in ("aim", "fire"):
            rect = next(rect for name, _, _, rect in game.control_rows() if name == action)
            click(game, rect.center)
            self.assertIsNone(game.editing_binding)


class PreferenceTests(unittest.TestCase):
    def test_saved_preferences_reload_with_conflicts_and_without_difficulty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            game = Game(menu=True, preferences=Preferences.load(path))
            game.menu_action("settings")
            game.menu_action("language_zh-CN")
            game.sfx_volume = .23
            game.preferences.bindings["move_up"] = pygame.K_q
            game.save_preferences()
            next_game = Game(menu=True, preferences=Preferences.load(path))
            self.assertEqual((next_game.language, next_game.sfx_volume), ("zh-CN", .23))
            self.assertEqual(next_game.preferences.conflicts(), {"move_up", "missile"})
            self.assertNotIn("difficulty", json.loads(path.read_text(encoding="utf-8")))
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_missing_and_malformed_settings_fall_back_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            self.assertEqual(Preferences.load(path).language, "en")
            for text in ("{", "[]", '{"language": [], "sfx_volume": true, "bindings": []}',
                         '{"sfx_volume": NaN, "music_volume": 1e999, "bindings": {"pause": -1}}'):
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    prefs = Preferences.load(path)
                    self.assertEqual((prefs.language, prefs.sfx_volume, prefs.music_volume), ("en", .45, .35))
                    self.assertEqual(prefs.bindings, DEFAULT_BINDINGS)
            path.write_text('{"bindings": {"move_up": 1073741906, "pause": false}, "sfx_volume": 0}', encoding="utf-8")
            prefs = Preferences.load(path)
            self.assertEqual(prefs.bindings["move_up"], pygame.K_UP)
            self.assertEqual(prefs.bindings["pause"], pygame.K_ESCAPE)
            self.assertEqual(prefs.sfx_volume, 0)

    def test_save_failure_keeps_current_preferences_usable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing" / "preferences.json"
            game = Game(menu=True, preferences=Preferences.load(path))
            game.menu_action("settings")
            game.menu_action("language_zh-CN")
            self.assertTrue(game.save_failed)
            self.assertEqual(game.language, "zh-CN")
            game.menu_action("settings_back")
            self.assertEqual(game.state, "main_menu")
