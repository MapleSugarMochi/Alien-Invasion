"""输入与游戏规则协调；显示层只读取这些状态。"""
from dataclasses import dataclass, field
import random

import pygame
from pygame import Vector2

from entities import Boss, Enemy, Meteor, Pickup, Player
from geometry import moving_hit
from weapons import ArcAttack, Missile, Projectile, SupportController, WeaponController
from settings import DIFFICULTIES, HEIGHT, HUD_HEIGHT, WIDTH
from waves import WaveController


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

    @property
    def display_aim(self):
        return Vector2(max(0, min(WIDTH, self.aim.x)), max(HUD_HEIGHT, min(HEIGHT, self.aim.y)))

    def clear(self) -> None:
        self.keys.clear()
        self.fire = False


class Game:
    def __init__(self, difficulty="standard", seed=None, menu=False) -> None:
        self.running = True
        self.state = "main_menu" if menu else "playing"
        self.input = InputState()
        self.player = Player()
        self.enemies = []
        self.time = 0.0
        self.weapons = WeaponController()
        self.projectiles = []
        self.enemy_bullets = []
        self.meteors = []
        self.score = self.kills = 0
        self.effects = []
        self.difficulty = DIFFICULTIES[difficulty]
        self.rng = random.Random(seed)
        self._entity_id = 0
        self.wave = WaveController(1, 0)
        self.phase = "waves"
        self.phase_until = 0.0
        self.next_meteor = self.difficulty.meteor_interval
        self.meteor_warning = None
        self.next_drop = 7.0
        self.pickups = []
        self.journal = []
        self.boss = None
        self.selected_difficulty = difficulty
        self.hover = Vector2(-1, -1)
        self.commands = []
        self.arc_effects = []
        self.energy_units = 0
        self.support = SupportController()
        self.sfx_volume, self.music_volume = .45, .35
        self.audio_return_state = "main_menu"
        self.sound_events = []

    @property
    def targets(self):
        return self.enemies + ([self.boss] if self.boss and self.boss.hp > 0 else [])

    def restart(self):
        self.reset_session(self.difficulty.id)

    def reset_session(self, difficulty, menu=False):
        sfx, music = self.sfx_volume, self.music_volume
        self.support.cancel()
        self.__init__(difficulty, menu=menu)
        self.sfx_volume, self.music_volume = sfx, music

    def start_session(self, difficulty):
        self.reset_session(difficulty)
        self.record("session_start", difficulty=difficulty)

    def to_menu(self):
        self.reset_session(self.difficulty.id, menu=True)

    def buttons(self):
        """点击范围与显示共用，避免不同界面的命中区漂移。"""
        options = {
            "main_menu": [("setup", "开始游戏"), ("setup", "操作说明与难度"), ("audio", "声音设置"), ("quit", "退出")],
            "setup": [("easy", "简单"), ("standard", "标准"), ("hard", "困难"),
                      ("start", "开始战斗"), ("menu", "返回主菜单")],
            "paused": [("resume", "继续战斗"), ("restart", "重新开始"), ("audio", "声音设置"), ("menu", "返回主菜单")],
            "audio": [("sfx_down", "音效 -"), ("sfx_up", "音效 +"),
                      ("music_down", "音乐 -"), ("music_up", "音乐 +"), ("audio_back", "返回")],
            "victory": [("restart", "同难度再战"), ("menu", "返回主菜单")],
            "defeat": [("restart", "同难度重开"), ("menu", "返回主菜单")],
        }.get(self.state, [])
        if self.state == "setup":
            rects = [pygame.Rect(350 + i * 200, 460, 180, 48) for i in range(3)]
            rects += [pygame.Rect(440, 540 + i * 65, 400, 48) for i in range(2)]
        else:
            rects = [pygame.Rect(440, 380 + i * 65, 400, 48) for i in range(len(options))]
        return [(action, label, rect) for (action, label), rect in zip(options, rects)]

    def menu_action(self, action):
        if action in DIFFICULTIES:
            self.selected_difficulty = action
        elif action == "setup":
            self.state = "setup"
        elif action == "start":
            self.start_session(self.selected_difficulty)
        elif action == "resume":
            self.resume()
        elif action == "restart":
            self.restart()
        elif action == "menu":
            self.to_menu()
        elif action == "quit":
            self.running = False
            self.clear_battle_resources()
        elif action == "audio":
            self.audio_return_state = self.state
            self.state = "audio"
        elif action == "audio_back":
            self.state = self.audio_return_state
        elif action in ("sfx_down", "sfx_up", "music_down", "music_up"):
            attribute = "sfx_volume" if action.startswith("sfx") else "music_volume"
            change = .1 if action.endswith("up") else -.1
            setattr(self, attribute, round(max(0, min(1, getattr(self, attribute) + change)), 2))

    def finish(self, result):
        self.state = result
        self.clear_battle_resources()
        self.record(result, score=self.score, kills=self.kills)

    def clear_battle_resources(self):
        self.input.clear()
        self.commands.clear()
        self.pickups.clear()
        self.meteor_warning = None
        self.support.cancel()
        self.energy_units = 0

    def next_id(self):
        self._entity_id += 1
        return self._entity_id

    def record(self, name, **data):
        self.journal.append({"time": round(self.time, 6), "event": name, **data})

    def pause(self):
        self.state = "paused"
        self.input.clear()
        self.commands.clear()

    def resume(self):
        self.state = "playing"
        self.input.clear()
        self.commands.clear()

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self.menu_action("quit")
            elif event.type == pygame.KEYDOWN:
                if getattr(event, "repeat", False):
                    continue
                if self.state == "main_menu" and event.key == pygame.K_RETURN:
                    self.menu_action("setup")
                elif self.state == "setup" and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.menu_action({pygame.K_1: "easy", pygame.K_2: "standard", pygame.K_3: "hard"}[event.key])
                elif self.state == "setup" and event.key == pygame.K_RETURN:
                    self.menu_action("start")
                elif event.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.pause()
                    elif self.state == "paused":
                        self.resume()
                    elif self.state == "setup":
                        self.to_menu()
                elif self.state == "playing":
                    if event.key in (pygame.K_q, pygame.K_e, pygame.K_x) and event.key not in self.input.keys:
                        self.commands.append({pygame.K_q: "missile", pygame.K_e: "arc", pygame.K_x: "support"}[event.key])
                    self.input.keys.add(event.key)
                elif self.state in ("defeat", "victory") and event.key == pygame.K_r:
                    self.restart()
            elif event.type == pygame.KEYUP:
                self.input.keys.discard(event.key)
            elif event.type == pygame.MOUSEMOTION:
                self.input.aim.update(event.pos)
                self.hover.update(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "playing":
                    self.input.fire = True
                    self.input.aim.update(event.pos)
                else:
                    for action, _, rect in self.buttons():
                        if rect.collidepoint(event.pos):
                            self.menu_action(action)
                            break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.input.fire = False
            elif event.type == pygame.WINDOWFOCUSLOST:
                if self.state == "playing":
                    self.pause()
                self.input.clear()

    def update(self, dt: float) -> None:
        if not self.running or self.state != "playing":
            return
        self.weapons.expire(self.time)
        self.expire_support()
        # 同刻 X 先于伤害，避免已启动的支援仍收到当帧回能。
        for command in sorted(self.commands, key=lambda c: c != "support"):
            if command == "support":
                self.try_support()
            elif self.weapons.try_activate(command, self.time):
                self.record("weapon_activate", kind=command)
        self.commands.clear()
        self.timed_events()
        self.update_support()
        self.fire_weapon()
        # 保留整帧时间，以小步处理运动；胜负在整帧最后统一判定。
        remaining = dt
        while remaining > 1e-9:
            step = min(remaining, 1 / 60)
            if self.input.fire and self.input.in_battle and self.weapons.ready_at > self.time + 1e-9:
                step = min(step, self.weapons.ready_at - self.time)
            deadlines = [self.next_drop]
            deadlines += self.support.deadlines()
            if self.weapons.active != "bullet":
                deadlines.append(self.weapons.active_until)
            if self.phase in ("waves", "rest"):
                deadlines += [self.next_meteor - .6, self.next_meteor]
            if self.phase == "waves":
                if self.wave.queue and len(self.enemies) < self.difficulty.enemy_cap:
                    deadlines.append(self.wave.next_spawn)
            if self.phase == "rest":
                deadlines.append(self.phase_until)
            if self.phase == "boss_warning":
                deadlines.append(self.phase_until)
            if self.boss:
                deadlines += [self.boss.next_round, self.boss.transition_until] + self.boss.burst
            deadlines += [enemy.next_shot for enemy in self.enemies if enemy.kind != "scout"]
            for deadline in deadlines:
                if deadline > self.time + 1e-9:
                    step = min(step, deadline - self.time)
            self._step(step)
            remaining -= step
        if self.player.hp <= 0:
            self.finish("defeat")
        elif self.boss and self.boss.hp <= 0:
            self.finish("victory")

    def _step(self, dt):
        self.time += dt
        self.weapons.expire(self.time)
        # 支援采用 [start, end)，截止时先清空，再允许该时刻常态伤害回能。
        self.expire_support()
        self.player.update(dt, self.input.movement, self.input.display_aim)
        for enemy in self.enemies:
            for direction in enemy.update(dt, self.time, self.player.pos):
                self.enemy_bullets.append(Projectile(enemy.pos.copy(), direction * enemy.bullet_speed,
                                                     enemy.bullet_damage, 4, "enemy", float("inf")))
        if self.boss:
            for direction in self.boss.update(dt, self.time, self.player.pos):
                self.enemy_bullets.append(Projectile(self.boss.pos.copy(), direction * 240 * self.difficulty.bullet_speed,
                                                     self.difficulty.hit(15), 4, "enemy", float("inf")))
            if not self.boss.entering:
                self.phase = "boss_fight"
        for meteor in self.meteors:
            meteor.update(dt)
        self.update_support()
        for projectile in self.projectiles:
            self.resolve_projectile(projectile, dt, self.targets + self.meteors)
        for projectile in self.enemy_bullets:
            self.resolve_projectile(projectile, dt, self.meteors + [self.player])
        self.contacts()
        for enemy in self.enemies:
            if enemy.gone and enemy.hp > 0:
                self.record("enemy_left", id=enemy.id, kind=enemy.kind)
        self.enemies = [e for e in self.enemies if e.hp > 0 and not e.gone]
        self.meteors = [m for m in self.meteors if m.hp > 0 and m.pos.y - m.radius <= HEIGHT
                        and -m.radius <= m.pos.x <= WIDTH + m.radius]
        for pickup in self.pickups:
            pickup.update(dt)
            if not pickup.expired(self.time) and self.player.pos.distance_to(pickup.pos) <= self.player.radius + pickup.radius:
                if self.collect(pickup):
                    self.record("pickup", kind=pickup.kind)
                    self.sound_events.append("pickup")
        self.pickups = [p for p in self.pickups if not p.expired(self.time)]
        self.projectiles = [p for p in self.projectiles if p.alive]
        self.enemy_bullets = [p for p in self.enemy_bullets if p.alive]
        self.effects = [e for e in self.effects if e[0] > self.time]
        self.arc_effects = [e for e in self.arc_effects if e[0] > self.time]
        self.timed_events()
        self.fire_weapon()

    def timed_events(self):
        if self.player.hp <= 0 or (self.boss and self.boss.hp <= 0):
            return
        if self.time + 1e-9 >= self.next_drop:
            x = self.rng.uniform(48, 1232)
            if self.player.pos.distance_to(Vector2(x, 78)) <= 28:
                x = 48 if self.player.pos.x > 640 else 1232
            kind = self.rng.choice(("health", "missile", "arc"))
            self.pickups.append(Pickup(self.next_id(), Vector2(x, 78), self.time, kind))
            self.record("drop", kind=kind)
            self.next_drop += 7
        if self.phase in ("waves", "rest"):
            if self.meteor_warning is None and self.time + 1e-9 >= self.next_meteor - .6:
                if len(self.meteors) < self.difficulty.meteor_cap:
                    radius = self.rng.choice((22, 36))
                    self.meteor_warning = (self.next_meteor, self.rng.uniform(radius, WIDTH - radius), radius)
                    self.record("meteor_warning")
                else:
                    self.next_meteor = self.time + self.difficulty.meteor_interval + .6
            if self.meteor_warning and self.time + 1e-9 >= self.meteor_warning[0]:
                _, x, radius = self.meteor_warning
                self.meteors.append(Meteor(self.next_id(), Vector2(x, HUD_HEIGHT - radius), radius,
                                           40 if radius == 22 else 80,
                                           Vector2(self.rng.uniform(-35, 35), self.rng.uniform(100, 140))))
                self.record("meteor_spawn")
                self.meteor_warning = None
                self.next_meteor = self.time + self.difficulty.meteor_interval
        if self.phase == "rest" and self.time + 1e-9 >= self.phase_until:
            self.phase = "waves"
            self.wave = WaveController(self.wave.number + 1, self.time)
        if self.phase == "waves":
            enemy = self.wave.update(self.time, len(self.enemies), self.difficulty, self._entity_id + 1)
            if enemy:
                self.next_id()
                self.enemies.append(enemy)
                self.record("enemy_spawn", id=enemy.id, kind=enemy.kind, wave=self.wave.number)
            if not self.wave.queue and not self.enemies:
                self.record("wave_end", wave=self.wave.number)
                self.phase = "rest" if self.wave.number < 12 else "meteor_clear"
                self.phase_until = self.time + 3
                if self.wave.number == 12:
                    self.meteor_warning = None
        if self.phase == "meteor_clear" and not self.meteors:
            self.phase = "boss_warning"
            self.phase_until = self.time + 1.5
            self.record("boss_warning")
        if self.phase == "boss_warning" and self.time + 1e-9 >= self.phase_until:
            self.boss = Boss(self.next_id(), self.difficulty)
            self.phase = "boss_entry"
            self.record("boss_spawn")

    def fire_weapon(self):
        if self.player.hp > 0 and not (self.boss and self.boss.hp <= 0) and self.input.fire and self.input.in_battle:
            projectile = self.weapons.try_fire(self.time, self.player, self.input.display_aim, self.targets)
            if projectile:
                self.sound_events.append(self.weapons.active)
                if isinstance(projectile, ArcAttack):
                    points = [self.player.pos.copy()] + [t.pos.copy() for t in projectile.targets]
                    for target, damage in zip(projectile.targets, (18, 13, 10)):
                        self.apply_damage(target, damage, "arc")
                    if len(points) > 1:
                        self.arc_effects.append((self.time + .12, points))
                else:
                    self.projectiles.append(projectile)

    def try_support(self):
        if self.energy_units < 1000 or self.support.active:
            self.support.failed_until = self.time + .3
            return False
        self.energy_units = 0
        self.support.start(self.time)
        self.record("support_start")
        return True

    def expire_support(self):
        if self.support.expire(self.time):
            self.energy_units = 0
            self.record("support_end")

    def update_support(self):
        for event, number, ids in self.support.update(self.time, self.targets, self.input.display_aim):
            self.record("support_" + event, round=number, targets=ids)
            if event == "hit":
                if ids:
                    self.sound_events.append("support")
                targets = {t.id: t for t in self.targets}
                for target_id in ids:
                    target = targets.get(target_id)
                    if target and target.damageable and target.on_screen:
                        amount = target.max_hp // 10 if isinstance(target, Boss) else target.hp
                        self.apply_damage(target, amount, "support")
                        self.effects.append((self.time + .4, target.pos.copy(), 45))
            elif event == "round" and ids:
                self.sound_events.append("lock")
        if self.support.active:
            self.energy_units = 0

    def collect(self, pickup):
        if pickup.kind == "health":
            if self.player.hp >= 100:
                return False
            self.player.hp = min(100, self.player.hp + 25)
        else:
            if self.weapons.charges[pickup.kind] >= 3:
                return False
            self.weapons.charges[pickup.kind] += 1
        pickup.consumed = True
        return True

    def resolve_projectile(self, projectile, dt, targets):
        if not projectile.alive or not (0 <= projectile.pos.x <= WIDTH and 0 <= projectile.pos.y <= HEIGHT):
            projectile.alive = False
            return
        if isinstance(projectile, Missile):
            projectile.turn(dt, self.targets, self.input.display_aim)
        start, end, fraction, expired = projectile.advance(dt)
        hits = []
        for target in targets:
            if target.hp <= 0 or (isinstance(target, (Enemy, Boss)) and not target.damageable):
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
                if isinstance(projectile, Missile):
                    self.sound_events.append("explosion")
                    # 主目标只吃一次直接伤害；其余圆与爆炸圆相交才溅射。
                    for other in self.targets + self.meteors:
                        if other is not target and other.pos.distance_to(projectile.pos) <= 70 + other.radius:
                            self.apply_damage(other, 20, "missile_splash")
                    self.effects.append((self.time + .35, projectile.pos.copy(), 70))
            self.effects.append((self.time + .18, projectile.pos.copy(), 12))
        elif expired:
            projectile.alive = False

    def apply_damage(self, target, amount, source):
        if not target.damageable:
            return 0
        actual = min(target.hp, max(1, int(amount)))
        target.hp -= actual
        if isinstance(target, (Enemy, Boss)) and not self.support.active and source in ("bullet", "missile", "missile_splash", "arc"):
            self.energy_units = min(1000, self.energy_units + actual)
        if isinstance(target, Boss) and target.sync_phase(self.time):
            self.record("boss_transition", hp=target.hp)
            self.sound_events.append("phase")
        if isinstance(target, (Enemy, Boss)) and target.hp == 0:
            self.finalize_kill(target, source)
        return actual

    def finalize_kill(self, target, source="bullet"):
        if target.settled:
            return
        target.settled = True
        self.score += {"scout": 100, "shooter": 200, "heavy": 500, "boss": 5000}.get(target.kind, 0)
        self.kills += 1
        if not self.support.active:
            self.energy_units = min(1000, self.energy_units + {"scout": 20, "shooter": 40, "heavy": 80}.get(target.kind, 0))
        self.record("kill", id=target.id, kind=target.kind)

    def damage_player(self, amount):
        if self.time + 1e-9 < self.player.invulnerable_until or self.player.hp <= 0:
            return False
        self.player.hp = max(0, self.player.hp - int(amount))
        self.player.invulnerable_until = self.time + .8
        self.sound_events.append("hurt")
        return True

    def contacts(self):
        for target in self.targets + self.meteors:
            if target.hp <= 0:
                continue
            difference = self.player.pos - target.pos
            minimum = self.player.radius + target.radius
            if difference.length_squared() > minimum * minimum:
                continue
            accepted = self.damage_player(self.difficulty.hit(25 if isinstance(target, Meteor) else 20))
            if accepted and isinstance(target, Enemy):
                self.apply_damage(target, target.hp, "contact")
            direction = difference.normalize() if difference.length_squared() else Vector2(0, 1)
            self.player.pos += direction * max(32, minimum - difference.length() + .01)
            self.player.clamp()

