import unittest
from pygame import Vector2

from entities import Boss, Enemy, Pickup, Player
from game import Game
from weapons import ArcAttack, Missile, WeaponController, arc_chain


class SpecialWeaponTests(unittest.TestCase):
    def test_three_charges_exclusive_duration_and_shared_cooldown(self):
        player = Player()
        weapons = WeaponController()
        self.assertFalse(weapons.try_activate("missile", 0))
        weapons.try_fire(0, player)
        weapons.charges.update(missile=3, arc=3)
        self.assertTrue(weapons.try_activate("missile", 0))
        self.assertEqual(weapons.ready_at, .4)
        self.assertIsNone(weapons.try_fire(.399, player))
        self.assertIsInstance(weapons.try_fire(.4, player), Missile)
        self.assertFalse(weapons.try_activate("arc", .4))
        self.assertEqual(weapons.charges["arc"], 3)
        weapons.try_fire(4.8, player)
        weapons.expire(5)
        self.assertEqual(weapons.active, "bullet")
        self.assertAlmostEqual(weapons.ready_at, 5.2)
        self.assertIsNone(weapons.try_fire(5.199, player))

    def test_pickup_capacity_and_recharging_during_active(self):
        game = Game()
        for _ in range(3):
            self.assertTrue(game.collect(Pickup(1, Vector2(), 0, "missile")))
        excess = Pickup(2, Vector2(), 0, "missile")
        self.assertFalse(game.collect(excess))
        self.assertFalse(excess.consumed)
        game.weapons.try_activate("missile", 0)
        self.assertTrue(game.collect(excess))
        self.assertEqual(game.weapons.charges["missile"], 1)

    def test_missile_search_from_own_position_and_turn_limit(self):
        missile = Missile(Vector2(1000, 400), Vector2(1, 0))
        target = Enemy(1, Vector2(1000, 200))
        missile.turn(.125, [target], target.pos)
        self.assertEqual(missile.target_id, 1)
        self.assertAlmostEqual(missile.velocity.angle_to(Vector2(1, 0)), 45)
        before = missile.velocity.copy()
        target.hp = 0
        missile.turn(.1, [target], target.pos)
        self.assertEqual(missile.velocity, before)
        self.assertIsNone(missile.target_id)
        _, _, _, expired = missile.advance(3)
        self.assertTrue(expired)

    def test_explosion_main_target_once_and_other_targets(self):
        game = Game()
        game.enemies = [Enemy(1, Vector2(200, 200), hp=120), Enemy(2, Vector2(245, 200), hp=120)]
        game.meteors.clear()
        game.input.aim.update(200, 200)
        shot = Missile(Vector2(100, 200), Vector2(1, 0))
        game.resolve_projectile(shot, .3, game.targets)
        self.assertEqual([t.hp for t in game.enemies], [60, 100])
        self.assertFalse(shot.alive)

    def test_arc_cone_boundaries_chain_and_damage(self):
        game = Game()
        game.player.pos.update(400, 400)
        game.player.direction.update(1, 0)
        enemies = [Enemy(1, Vector2(600, 600), hp=50), Enemy(2, Vector2(700, 600), hp=50),
                   Enemy(3, Vector2(790, 600), hp=50), Enemy(4, Vector2(350, 400), hp=50)]
        chain = arc_chain(game.player, enemies[0].pos, enemies)
        self.assertEqual([e.id for e in chain], [1, 2, 3])
        game.enemies = enemies
        game.weapons.charges["arc"] = 3
        game.weapons.try_activate("arc", 0)
        game.input.fire = True
        game.input.aim = enemies[0].pos.copy()
        game.fire_weapon()
        self.assertEqual([e.hp for e in enemies], [32, 37, 40, 50])

    def test_empty_arc_uses_cooldown_and_entry_boss_is_excluded(self):
        weapons = WeaponController()
        weapons.charges["arc"] = 3
        weapons.try_activate("arc", 0)
        result = weapons.try_fire(0, Player(), Vector2(640, 180), [])
        self.assertIsInstance(result, ArcAttack)
        self.assertFalse(result.targets)
        self.assertIsNone(weapons.try_fire(.1, Player()))
        game = Game()
        boss = Boss(1, game.difficulty)
        boss.pos.update(640, 180)
        self.assertFalse(arc_chain(game.player, boss.pos, [boss]))

    def test_drop_random_branches_do_not_depend_on_capacity(self):
        class ChoiceRandom:
            def uniform(self, a, b):
                return (a + b) / 2
            def choice(self, candidates):
                self.asserted = tuple(candidates)
                return candidates[self.index]
        for index, kind in enumerate(("health", "missile", "arc")):
            game = Game()
            game.phase = "boss_fight"
            game.time = 7
            game.rng = ChoiceRandom()
            game.rng.index = index
            game.weapons.charges.update(missile=3, arc=3)
            game.timed_events()
            self.assertEqual(game.rng.asserted, ("health", "missile", "arc"))
            self.assertEqual(game.pickups[0].kind, kind)

    def test_key_hold_never_queues_second_activation(self):
        import pygame
        game = Game()
        game.weapons.charges["arc"] = 3
        press = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)
        game.handle_events([press, press, press])
        self.assertEqual(game.commands, ["arc"])
        game.update(0)
        self.assertEqual(game.weapons.active, "arc")
        game.weapons.charges["arc"] = 3
        game.time = 5
        game.handle_events([press])
        game.update(0)
        self.assertEqual(game.weapons.active, "bullet")
        self.assertEqual(game.weapons.charges["arc"], 3)
