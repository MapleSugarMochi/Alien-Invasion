import unittest
from collections import Counter

import pygame

from game import Game
from settings import DIFFICULTIES, LEVEL_CONFIGS, LEVELS, WAVES


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

    def test_level_one_and_two_preserve_original_content(self):
        runs = []
        for level in (1, 2):
            game = Game(menu=True)
            click_button(game, "level_select")
            click_button(game, f"level_{level}")
            game.rng.seed(5)
            game.input.fire = True
            for _ in range(600):
                game.update(1 / 60)
            runs.append((game.state, game.time, game.player.hp, game.score,
                         game.wave.number, game.phase, game.journal[1:]))
            self.assertEqual(game.level_config.waves, WAVES)
            self.assertEqual(game.level_config.boss_base_hp, 2400)
        self.assertEqual(runs[0], runs[1])

    def test_level_configuration_reaches_every_wave_and_boss_without_leaking(self):
        for difficulty, base_boss_hp in (("easy", 1920), ("standard", 2400), ("hard", 3000)):
            # 同一实例反复切换，验证关卡 3 的增量不会污染后续关卡 2／1。
            game = Game(menu=True)
            for level in (3, 2, 1, 3):
                with self.subTest(difficulty=difficulty, level=level):
                    game.start_session(difficulty, level)
                    game.next_meteor = game.next_drop = float("inf")
                    totals = Counter()
                    for number in range(1, 13):
                        planned = Counter(game.wave.queue) + Counter(e.kind for e in game.enemies)
                        expected = LEVEL_CONFIGS[level].waves[number - 1]
                        self.assertEqual(game.wave.number, number)
                        self.assertEqual(planned, Counter(dict(zip(("scout", "shooter", "heavy"), expected[:3]))))
                        self.assertEqual(game.wave.interval, WAVES[number - 1][3])
                        totals.update(planned)
                        game.wave.queue.clear()
                        game.enemies.clear()
                        game.timed_events()
                        if number < 12:
                            game.time = game.phase_until
                            game.timed_events()
                    self.assertEqual(totals, {"scout": 75, "shooter": 43, "heavy": 24} if level == 3
                                     else {"scout": 62, "shooter": 36, "heavy": 20})
                    game.time = game.phase_until
                    game.timed_events()
                    self.assertEqual(game.phase, "boss_entry")
                    expected_hp = base_boss_hp * 14 // 10 if level == 3 else base_boss_hp
                    self.assertEqual((game.boss.hp, game.boss.max_hp), (expected_hp, expected_hp))
                    self.assertEqual(game.boss.health_phase(), 1)
                    game.boss.hp = expected_hp * 2 // 3
                    self.assertEqual(game.boss.health_phase(), 2)
                    game.boss.hp = expected_hp // 3 - 1
                    self.assertEqual(game.boss.health_phase(), 3)
