"""输入与游戏规则协调；显示层只读取这些状态。"""
from dataclasses import dataclass, field

import pygame
from pygame import Vector2

from entities import Enemy, Meteor, Player
from geometry import moving_hit
from weapons import Projectile, WeaponController
from settings import HEIGHT, HUD_HEIGHT, WIDTH


@dataclass
class InputState:
    keys: set[int] = field(default_factory=set)
    aim: Vector2 = field(default_factory=lambda: Vector2(640, 180))
    fire: bool = False

    @property
    def movement(self) -> Vector2:
        return Vector2(int(pygame.K_d in self.keys) - int(pygame.K_a in self.keys),
                       int(pygame.K_s in self.keys) - int(pygame.K_w in self.keys))

    @property
    def in_battle(self) -> bool:
        return 0 <= self.aim.x <= WIDTH and HUD_HEIGHT <= self.aim.y <= HEIGHT

    def clear(self) -> None:
        self.keys.clear()
        self.fire = False


class Game:
    def __init__(self) -> None:
        self.running = True
        self.state = "playing"
        self.input = InputState()
        self.player = Player()
        self.enemies = [Enemy(1, Vector2(640, 180))]
        self.time = 0.0
        self.weapons = WeaponController()
        self.projectiles = []
        self.enemy_bullets = []
        self.meteors = [Meteor(2, Vector2(950, 140))]
        self.score = self.kills = 0
        self.effects = []
        self._next_demo_shot = 1.5

    def pause(self):
        self.state = "paused"
        self.input.clear()

    def resume(self):
        self.state = "playing"
        self.input.clear()

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.pause()
                    elif self.state == "paused":
                        self.resume()
                elif self.state == "playing":
                    self.input.keys.add(event.key)
            elif event.type == pygame.KEYUP:
                self.input.keys.discard(event.key)
            elif event.type == pygame.MOUSEMOTION:
                self.input.aim.update(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.input.fire = self.state == "playing"
                self.input.aim.update(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.input.fire = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                if self.state == "playing":
                    self.pause()
                self.input.clear()

    def update(self, dt: float) -> None:
        if not self.running or self.state != "playing":
            return
        self.fire_weapon()
        # 保留整帧时间，以小步处理运动；胜负在整帧最后统一判定。
        remaining = dt
        while remaining > 1e-9:
            step = min(remaining, 1 / 60)
            if self.input.fire and self.input.in_battle and self.weapons.ready_at > self.time + 1e-9:
                step = min(step, self.weapons.ready_at - self.time)
            self._step(step)
            remaining -= step
        if self.player.hp <= 0:
            self.state = "defeat"
            self.input.clear()

    def _step(self, dt):
        self.time += dt
        self.player.update(dt, self.input.movement, self.input.aim)
        for enemy in self.enemies:
            enemy.previous = enemy.pos.copy()
        for meteor in self.meteors:
            meteor.update(dt)
        self.fire_weapon()
        if self.enemies and self.time >= self._next_demo_shot:
            direction = self.player.pos - self.enemies[0].pos
            if direction.length_squared():
                self.enemy_bullets.append(Projectile(self.enemies[0].pos.copy(), direction.normalize() * 250,
                                                     10, 4, "enemy", float("inf")))
            self._next_demo_shot = self.time + 1.5
        for projectile in self.projectiles:
            self.resolve_projectile(projectile, dt, self.enemies + self.meteors)
        for projectile in self.enemy_bullets:
            self.resolve_projectile(projectile, dt, self.meteors + [self.player])
        self.contacts()
        self.enemies = [e for e in self.enemies if e.hp > 0]
        self.meteors = [m for m in self.meteors if m.hp > 0 and m.pos.y - m.radius <= HEIGHT]
        self.projectiles = [p for p in self.projectiles if p.alive]
        self.enemy_bullets = [p for p in self.enemy_bullets if p.alive]
        self.effects = [e for e in self.effects if e[0] > self.time]

    def fire_weapon(self):
        if self.input.fire and self.input.in_battle:
            projectile = self.weapons.try_fire(self.time, self.player)
            if projectile:
                self.projectiles.append(projectile)

    def resolve_projectile(self, projectile, dt, targets):
        start, end, fraction, expired = projectile.advance(dt)
        hits = []
        for target in targets:
            if target.hp <= 0 or (isinstance(target, Enemy) and not target.damageable):
                continue
            target_end = target.previous.lerp(target.pos, fraction)
            hit = moving_hit(start, end, target.previous, target_end, target.radius + projectile.radius)
            if hit is not None:
                # 敌弹同刻先由陨石吸收；稳定 ID 决定其他平局。
                hits.append((hit, getattr(target, "id", 10**9), target))
        if hits:
            t, _, target = min(hits, key=lambda item: (item[0], item[1]))
            projectile.pos = start.lerp(end, t)
            projectile.alive = False
            if projectile.source == "enemy":
                if target is self.player:
                    self.damage_player(projectile.damage)
            else:
                self.apply_damage(target, projectile.damage, projectile.source)
            self.effects.append((self.time + .18, projectile.pos.copy(), 12))
        elif expired:
            projectile.alive = False

    def apply_damage(self, target, amount, source):
        if not target.damageable:
            return 0
        actual = min(target.hp, max(1, int(amount)))
        target.hp -= actual
        if isinstance(target, Enemy) and target.hp == 0:
            self.finalize_kill(target)
        return actual

    def finalize_kill(self, target):
        if target.settled:
            return
        target.settled = True
        self.score += {"scout": 100, "shooter": 200, "heavy": 500}.get(target.kind, 0)
        self.kills += 1

    def damage_player(self, amount):
        if self.time + 1e-9 < self.player.invulnerable_until or self.player.hp <= 0:
            return False
        self.player.hp = max(0, self.player.hp - int(amount))
        self.player.invulnerable_until = self.time + .8
        return True

    def contacts(self):
        for target in self.enemies + self.meteors:
            if target.hp <= 0:
                continue
            difference = self.player.pos - target.pos
            minimum = self.player.radius + target.radius
            if difference.length_squared() > minimum * minimum:
                continue
            accepted = self.damage_player(25 if isinstance(target, Meteor) else 20)
            if accepted and isinstance(target, Enemy):
                self.apply_damage(target, target.hp, "contact")
            direction = difference.normalize() if difference.length_squared() else Vector2(0, 1)
            self.player.pos += direction * max(32, minimum - difference.length() + .01)
            self.player.clamp()

