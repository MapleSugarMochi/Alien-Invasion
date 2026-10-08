"""复杂教学条件、检查点清理和公开输入端到端回归。"""
import unittest
from collections import Counter

import pygame
from pygame import Vector2

from entities import Pickup, Meteor
from game import Game
from preferences import Preferences
from settings import TUTORIAL_ARC_TARGETS
from tools.tutorial_pilot import controls, tap, tutorial_pilot
from weapons import Projectile


def scene(step):
    game = Game(level=1, seed=5)
    game.tutorial.step = step
    game.tutorial.completed = list(range(1, step))
    game.tutorial.enter(game)
    return game


def click(game, action):
    rect = next(rect for name, _, rect in game.buttons() if name == action)
    game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center),
                        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center)])


class TutorialTests(unittest.TestCase):
    def test_combat_hints_use_real_conditions_once_per_checkpoint(self):
        game = scene(8)
        game.update(.1)
        self.assertFalse(game.tutorial.hints_seen)
        game.player.hp = 50
        game.update(.1)
        self.assertEqual(game.tutorial.notice, "tutorial_combat_health_hint")
        game.weapons.charges["arc"] = 3
        game.update(.1)
        game.update(.1)
        hints = [e["hint"] for e in game.journal if e["event"] == "tutorial_hint"]
        self.assertEqual(hints, ["low_hp", "weapon_ready"])
        self.assertEqual(game.tutorial.step, 8)

    def test_pause_also_freezes_step_transition(self):
        game = Game(level=1)
        click(game, "tutorial_continue")
        game.pause()
        game.update(10)
        game.resume()
        game.update(.4)
        self.assertEqual(game.tutorial.step, 1)
        game.update(.4)
        self.assertEqual(game.tutorial.step, 2)

    def test_aim_marker_still_works_after_last_target_destroyed(self):
        game = scene(2)
        for _ in range(3):
            game.update(.02)
            game.apply_damage(game.enemies[0], 20, "bullet")
        game.update(.5)
        self.assertFalse(game.tutorial.transitioning)
        controls(game, aim=game.tutorial.aim_target)
        game.update(.02)
        self.assertTrue(game.tutorial.transitioning)

    def test_contact_energy_cannot_bypass_support_shooting_task(self):
        game = scene(7)
        game.energy_units = 1000
        self.assertFalse(game.try_support())
        self.assertFalse(game.support.active or game.tutorial.support_seen)

    def test_intro_needs_no_movement_and_transition_freezes_battle(self):
        game = Game(level=1)
        position = game.player.pos.copy()
        game.update(20)
        self.assertEqual(game.tutorial.step, 1)
        self.assertFalse(game.enemies or game.pickups or game.meteors)
        self.assertEqual(game.player.pos, position)
        click(game, "tutorial_continue")
        frozen = game.time
        game.update(.4)
        self.assertEqual(game.time, frozen)
        self.assertEqual(game.tutorial.step, 1)
        game.update(.4)
        self.assertEqual(game.tutorial.step, 2)
        self.assertFalse(game.input.fire or game.input.keys)
        self.assertEqual(game.tutorial.completed, [1])

    def test_fixed_training_preserves_chosen_difficulty_and_preferences(self):
        preferences = Preferences(language="zh-CN")
        preferences.bindings["move_right"] = pygame.K_RIGHT
        game = Game("hard", preferences=preferences, level=1)
        self.assertEqual((game.difficulty.id, game.difficulty.enemy_cap), ("standard", 2))
        self.assertIn("Right", " ".join(game.tutorial.lines(game)))
        game.restart()
        self.assertEqual((game.selected_difficulty, game.language), ("hard", "zh-CN"))
        game.menu_action("level_2")
        self.assertEqual(game.difficulty.id, "hard")
        self.assertIs(game.preferences, preferences)
        self.assertIsNone(game.tutorial)

    def test_collision_kill_does_not_count_as_shooting(self):
        game = scene(2)
        game.update(0)
        target = game.enemies[0]
        game.apply_damage(target, target.hp, "contact")
        self.assertEqual(game.tutorial.progress, 0)
        game.update(.02)
        self.assertTrue(game.enemies)
        self.assertNotEqual(game.enemies[0].id, target.id)

    def test_last_target_requires_aim_and_release_fire(self):
        game = scene(2)
        for _ in range(3):
            game.update(.02)
            game.apply_damage(game.enemies[0], 20, "bullet")
        game.tutorial.aim_seen = True
        controls(game, fire=True)
        game.update(.5)
        self.assertFalse(game.tutorial.transitioning)
        controls(game)
        game.update(.39)
        self.assertFalse(game.tutorial.transitioning)
        game.update(.02)
        self.assertTrue(game.tutorial.transitioning)

    def test_destroyed_meteor_retries_and_preserves_completed_dodges(self):
        game = scene(3)
        game.tutorial.progress = 1
        game.update(1.5)
        meteor = game.tutorial.meteor
        self.assertIsNotNone(meteor)
        game.apply_damage(meteor, 40, "bullet")
        game.update(.01)
        self.assertEqual((game.tutorial.step, game.tutorial.progress, game.tutorial.retries), (3, 1, 1))
        self.assertEqual(game.tutorial.notice, "tutorial_meteor_shot")
        self.assertFalse(game.meteors or game.projectiles or game.meteor_warning)

    def test_meteor_requires_seventy_pixels_and_no_contact(self):
        for distance, contacted, expected in ((69, False, 0), (70, False, 1), (100, True, 0)):
            with self.subTest(distance=distance, contacted=contacted):
                game = scene(3)
                game.update(1.5)
                game.tutorial.meteor.pos.y = 750
                game.player.pos.x = game.tutorial.dodge_origin + distance
                game.tutorial.meteor_contact = contacted
                game.tutorial.update(game)
                self.assertEqual(game.tutorial.progress, expected)

    def test_expired_supply_replaced_without_granting_charge(self):
        game = scene(5)
        game.update(0)
        first = game.pickups[0]
        game.update(10)
        self.assertEqual(game.weapons.charges["missile"], 0)
        self.assertEqual(game.tutorial.progress, 0)
        self.assertTrue(game.pickups)
        self.assertNotEqual(first.id, game.pickups[0].id)

    def test_full_capacity_does_not_consume_or_complete_pickup(self):
        for step, kind in ((4, "health"), (5, "missile"), (6, "arc")):
            game = scene(step)
            if kind == "health":
                game.player.hp = 100
            else:
                game.weapons.charges[kind] = 3
            supply = Pickup(game.next_id(), game.player.pos.copy(), game.time, kind)
            self.assertFalse(game.collect(supply))
            self.assertFalse(supply.consumed)
            self.assertEqual(game.tutorial.progress, 0)

    def test_activation_without_success_cannot_pass_or_extend_duration(self):
        game = scene(5)
        game.weapons.charges["missile"] = 3
        game.update(0)
        tap(game, "missile")
        game.update(.1)
        until = game.weapons.active_until
        tap(game, "missile")
        game.update(.1)
        self.assertEqual(game.weapons.active_until, until)
        game.update(5)
        self.assertEqual((game.tutorial.step, game.tutorial.retries), (5, 1))
        self.assertFalse(game.tutorial.skill_success)
        self.assertEqual(game.weapons.charges, {"missile": 0, "arc": 0})
        self.assertEqual(game.weapons.active, "bullet")

    def test_wrong_weapon_kill_is_not_missile_success(self):
        game = scene(5)
        game.weapons.charges["missile"] = 3
        game.update(0)
        game.apply_damage(game.enemies[0], 20, "bullet")
        self.assertFalse(game.tutorial.skill_success)

    def test_arc_requires_three_unique_targets_and_waits_full_duration(self):
        game = scene(6)
        game.weapons.charges["arc"] = 3
        game.update(0)
        game.tutorial.on_arc(game, [game.enemies[0]] * 3)
        self.assertFalse(game.tutorial.skill_success)
        controls(game, aim=TUTORIAL_ARC_TARGETS[0], fire=True)
        tap(game, "arc")
        game.update(.01)
        self.assertTrue(game.tutorial.skill_success)
        self.assertFalse(game.tutorial.transitioning)
        controls(game)
        game.update(4.98)
        self.assertFalse(game.tutorial.transitioning)
        game.update(.02)
        self.assertTrue(game.tutorial.transitioning)
        self.assertEqual(game.weapons.active, "bullet")

    def test_support_uses_real_energy_and_all_five_rounds(self):
        game = scene(7)
        for count in range(5):
            game.update(.02)
            game.apply_damage(game.enemies[0], 120, "bullet")
            self.assertEqual(game.energy_units, (count + 1) * 200)
        game.update(.02)
        tap(game, "support")
        game.update(.7)
        self.assertGreater(game.tutorial.support_hits, 0)
        self.assertFalse(game.tutorial.transitioning)
        self.assertEqual(game.energy_units, 0)
        game.update(6.79)
        self.assertFalse(game.tutorial.transitioning)
        game.update(.02)
        self.assertTrue(game.tutorial.transitioning)
        self.assertEqual(game.support.round_count, 5)
        self.assertFalse(game.support.active)

    def test_pause_settings_and_focus_preserve_skill_clock(self):
        game = scene(5)
        game.weapons.charges["missile"] = 3
        tap(game, "missile")
        game.update(.5)
        frozen = (game.time, game.weapons.active_until, game.tutorial.step, game.tutorial.completed[:])
        game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        game.update(10)
        game.menu_action("settings")
        game.menu_action("language_zh-CN")
        game.update(10)
        game.menu_action("settings_back")
        self.assertEqual(game.state, "paused")
        self.assertEqual((game.time, game.weapons.active_until, game.tutorial.step, game.tutorial.completed), frozen)
        game.resume()
        self.assertFalse(game.input.fire)
        self.assertEqual(game.language, "zh-CN")

    def test_combat_death_retry_clears_attacks_keeps_seven_steps(self):
        game = scene(8)
        game.projectiles.append(Projectile(Vector2(640, 400), Vector2(0, -100)))
        game.energy_units = 1000
        game.try_support()
        game.player.hp = 0
        game.update(.1)
        self.assertEqual(game.state, "tutorial_retry")
        click(game, "tutorial_retry")
        self.assertEqual((game.state, game.tutorial.step, game.player.hp, game.wave.number), ("playing", 8, 100, 1))
        self.assertEqual(game.tutorial.completed, list(range(1, 8)))
        self.assertFalse(game.projectiles or game.enemy_bullets or game.enemies or game.support.active)
        self.assertEqual((game.energy_units, game.weapons.charges), (0, {"missile": 0, "arc": 0}))

    def test_complete_public_input_flow_and_level_two_handoff(self):
        game = Game("hard", seed=5, level=1)
        for _ in range(18000):
            if game.state != "playing":
                break
            tutorial_pilot(game)
            game.update(1 / 60)
        self.assertEqual(game.state, "tutorial_complete")
        self.assertEqual(game.tutorial.completed, list(range(1, 9)))
        self.assertEqual(game.tutorial.retries, 0)
        spawns = [e for e in game.journal if e["event"] == "enemy_spawn"]
        self.assertEqual(Counter(e["kind"] for e in spawns), {"scout": 9, "shooter": 2, "heavy": 1})
        self.assertEqual([e["wave"] for e in game.journal if e["event"] == "wave_end"], [1, 2])
        self.assertFalse(any(e["event"] == "boss_spawn" for e in game.journal))
        preferences = game.preferences
        click(game, "tutorial_level_2")
        self.assertEqual((game.state, game.level, game.selected_difficulty), ("level_select", 2, "hard"))
        self.assertIsNone(game.tutorial)
        game.menu_action("level_2")
        self.assertEqual(game.difficulty.id, "hard")
        self.assertIs(game.preferences, preferences)

    def test_replay_and_quit_cancel_training_resources(self):
        game = scene(7)
        game.state = "tutorial_complete"
        click(game, "tutorial_restart")
        self.assertEqual((game.tutorial.step, game.tutorial.completed, game.time), (1, [], 0))
        game.menu_action("quit")
        game.update(1)
        self.assertFalse(game.running or game.enemies or game.pickups or game.support.active)
