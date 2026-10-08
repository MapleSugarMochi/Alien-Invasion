import string
import unittest

import pygame

from game import Game
from localization import TEXT


class LanguageTests(unittest.TestCase):
    def test_default_english_and_catalog_formats_match(self):
        game = Game(menu=True)
        self.assertEqual(game.language, "en")
        self.assertEqual(game.buttons()[0][1], "Start Game")
        self.assertEqual(set(TEXT["en"]), set(TEXT["zh-CN"]))
        formatter = string.Formatter()
        for key in TEXT["en"]:
            with self.subTest(key=key):
                fields = [
                    [(field, spec) for _, field, spec, _ in formatter.parse(TEXT[language][key])
                     if field is not None]
                    for language in ("en", "zh-CN")
                ]
                self.assertEqual(fields[0], fields[1])
                self.assertTrue(TEXT["en"][key] and TEXT["zh-CN"][key])
        self.assertEqual(game.text("result", score=123, kills=4, seconds=5.25),
                         "Score 123  /  Kills 4  /  Time 5.2s")
        with self.assertRaises(ValueError):
            Game(language="unsupported")

    def test_language_selection_is_only_available_in_settings(self):
        for state in ("main_menu", "level_select", "paused", "victory", "defeat", "playing"):
            with self.subTest(state=state):
                game = Game(menu=True)
                game.state = state
                self.assertFalse(any(action.startswith("language") for action, _, _ in game.buttons()))
                game.menu_action("language_zh-CN")
                self.assertEqual(game.language, "en")
        game = Game(menu=True)
        game.menu_action("settings")
        before = [(action, rect) for action, _, rect in game.buttons()]
        for language in ("zh-CN", "en"):
            rect = next(rect for action, _, rect in game.buttons() if action == "language_" + language)
            game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)])
            self.assertEqual((game.language, game.state), (language, "settings"))
            self.assertEqual(before, [(action, rect) for action, _, rect in game.buttons()])

    def test_f1_does_not_switch_language_in_any_screen(self):
        for state in ("main_menu", "level_select", "settings", "playing", "paused", "victory", "defeat"):
            with self.subTest(state=state):
                game = Game()
                game.state = state
                game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1),
                                    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, repeat=True)])
                self.assertEqual(game.language, "en")
                self.assertEqual(game.state, state)

    def test_language_survives_session_transitions(self):
        game = Game(menu=True)
        game.menu_action("settings")
        game.menu_action("language_zh-CN")
        game.menu_action("settings_back")
        game.menu_action("level_select")
        game.menu_action("hard")
        game.menu_action("level_1")
        self.assertEqual((game.language, game.difficulty.id), ("zh-CN", "hard"))
        game.pause()
        game.menu_action("settings")
        game.menu_action("settings_back")
        game.menu_action("restart")
        self.assertEqual((game.language, game.state), ("zh-CN", "level_select"))
        game.menu_action("level_1")
        for result in ("victory", "defeat"):
            game.finish(result)
            game.menu_action("restart")
            self.assertEqual(game.language, "zh-CN")
            game.menu_action("level_1")
        game.menu_action("menu")
        game.menu_action("level_select")
        game.menu_action("easy")
        game.menu_action("level_1")
        self.assertEqual((game.language, game.difficulty.id), ("zh-CN", "easy"))
        self.assertEqual(Game(menu=True).language, "en")

    def test_switch_during_special_weapon_and_support_preserves_battle(self):
        game = Game(seed=5)
        game.weapons.charges["missile"] = 3
        game.energy_units = 1000
        game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q),
                            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x),
                            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d),
                            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 180))])
        game.update(.1)
        game.pause()
        game.menu_action("settings")
        before = (game.time, game.player.hp, game.player.pos.copy(), game.score,
                  game.weapons.active, game.weapons.active_until, game.support.end_at,
                  tuple(game.support.rounds), game.input.keys.copy(), game.input.fire,
                  game.rng.getstate(), game.journal.copy(), game.commands.copy())
        game.menu_action("language_zh-CN")
        after = (game.time, game.player.hp, game.player.pos.copy(), game.score,
                 game.weapons.active, game.weapons.active_until, game.support.end_at,
                 tuple(game.support.rounds), game.input.keys.copy(), game.input.fire,
                 game.rng.getstate(), game.journal.copy(), game.commands.copy())
        self.assertEqual(before, after)
        self.assertEqual(game.language, "zh-CN")
        self.assertEqual(game.weapons.active, "missile")
        self.assertTrue(game.support.active)
