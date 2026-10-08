"""输入与游戏规则协调；显示层只读取这些状态。"""
from dataclasses import dataclass, field
import random

import pygame
from pygame import Vector2

from entities import Boss, Enemy, Meteor, Pickup, Player
from geometry import moving_hit
from localization import DEFAULT_LANGUAGE, TEXT, translate
from preferences import DEFAULT_BINDINGS, Preferences, key_name, valid_key
from weapons import ArcAttack, Missile, Projectile, SupportController, WeaponController
from settings import DIFFICULTIES, HEIGHT, HUD_HEIGHT, LEVELS, WIDTH
from waves import WaveController


@dataclass
class InputState:
    keys: set[int] = field(default_factory=set)
    aim: Vector2 = field(default_factory=lambda: Vector2(640, 180))
    fire: bool = False
    bindings: dict = field(default_factory=lambda: DEFAULT_BINDINGS.copy())

    @property
    def movement(self) -> Vector2:
        return Vector2(int(self.bindings["move_right"] in self.keys) - int(self.bindings["move_left"] in self.keys),
                       int(self.bindings["move_down"] in self.keys) - int(self.bindings["move_up"] in self.keys))

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
    def __init__(self, difficulty="standard", seed=None, menu=False, language=DEFAULT_LANGUAGE, preferences=None, level=1) -> None:
        if language not in TEXT:
            raise ValueError(f"Unsupported language: {language}")
        if level not in LEVELS:
            raise ValueError(f"Unsupported level: {level}")
        self.preferences = preferences if preferences is not None else Preferences(language=language)
        self.running = True
        self.state = "main_menu" if menu else "playing"
        self.input = InputState(bindings=self.preferences.bindings)
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
        self.level = level
        self.hover = Vector2(-1, -1)
        self.commands = []
        self.arc_effects = []
        self.energy_units = 0
        self.support = SupportController()
        self.settings_return_state = "main_menu"
        self.editing_binding = None
        self.dragging_slider = None
        self.save_failed = False
        self.ui_time = 0.0
        self.sound_events = []

    @property
    def language(self):
        return self.preferences.language

    @language.setter
    def language(self, value):
        self.preferences.language = value

    @property
    def sfx_volume(self):
        return self.preferences.sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, value):
        self.preferences.sfx_volume = value

    @property
    def music_volume(self):
        return self.preferences.music_volume

    @music_volume.setter
    def music_volume(self, value):
        self.preferences.music_volume = value

    @property
    def targets(self):
        return self.enemies + ([self.boss] if self.boss and self.boss.hp > 0 else [])

    def restart(self):
        self.reset_session(self.difficulty.id, menu=True)
        self.state = "level_select"

    def reset_session(self, difficulty, menu=False, level=None):
        preferences = self.preferences
        level = self.level if level is None else level
        self.support.cancel()
        self.__init__(difficulty, menu=menu, preferences=preferences, level=level)

    def start_session(self, difficulty, level=None):
        self.reset_session(difficulty, level=level)
        self.record("session_start", difficulty=difficulty, level=self.level)

    def to_menu(self):
        self.reset_session(self.difficulty.id, menu=True)

    def text(self, key, **values):
        return translate(self.language, key, **values)

    def binding_name(self, action):
        return key_name(self.preferences.bindings[action])

    def control_rows(self):
        """两列表格与点击范围共用；鼠标瞄准和射击为固定操作。"""
        rows = []
        for index, action in enumerate((*DEFAULT_BINDINGS, "aim", "fire")):
            label = self.binding_name(action) if action in DEFAULT_BINDINGS else self.text("mouse_move" if action == "aim" else "mouse_left")
            rows.append((action, self.text("action_" + action), label,
                         pygame.Rect(380, 170 + index * 38, 250, 38)))
        return rows

    def sliders(self):
        return [("sfx_volume", pygame.Rect(720, 325, 440, 24)),
                ("music_volume", pygame.Rect(720, 435, 440, 24))]

    def save_preferences(self):
        self.save_failed = not self.preferences.save()

    def set_slider(self, attribute, x):
        rect = next(rect for name, rect in self.sliders() if name == attribute)
        setattr(self, attribute, round(max(0, min(1, (x - rect.left) / rect.width)), 2))

    def open_settings(self):
        if self.state not in ("main_menu", "paused", "level_select"):
            return
        self.settings_return_state = self.state
        self.state = "settings"
        self.input.clear()
        self.commands.clear()
        self.editing_binding = self.dragging_slider = None

    def close_settings(self):
        self.save_preferences()
        self.state = self.settings_return_state
        self.editing_binding = self.dragging_slider = None
        self.input.clear()

    def buttons(self):
        """点击范围与显示共用，避免不同界面的命中区漂移。"""
        options = {
            "main_menu": [("level_select", "start_game"), ("settings", "settings"), ("quit", "quit")],
            "level_select": [(f"level_{number}", "level_name") for number in LEVELS] +
                            [("easy", "easy"), ("standard", "standard"), ("hard", "hard"), ("menu", "menu")],
            "paused": [("resume", "resume"), ("restart", "restart"), ("settings", "settings"), ("menu", "menu")],
            "settings": [("language_en", "english"), ("language_zh-CN", "chinese"),
                         ("reset_keys", "reset_keys"), ("settings_back", "back")],
            "victory": [("restart", "play_again"), ("menu", "menu")],
            "defeat": [("restart", "retry"), ("menu", "menu")],
        }.get(self.state, [])
        if self.state == "level_select":
            rects = [pygame.Rect(100 + i * 370, 190, 340, 310) for i in range(len(LEVELS))]
            rects += [pygame.Rect(390 + i * 170, 545, 150, 48) for i in range(3)]
            rects += [pygame.Rect(440, 625, 400, 48)]
        elif self.state == "settings":
            rects = [pygame.Rect(700, 205, 230, 48), pygame.Rect(950, 205, 230, 48),
                     pygame.Rect(80, 625, 250, 48), pygame.Rect(920, 625, 280, 48)]
        else:
            rects = [pygame.Rect(440, 380 + i * 65, 400, 48) for i in range(len(options))]
        buttons = [(action, self.text(key, number=int(action.removeprefix("level_")))
                    if key == "level_name" else self.text(key), rect)
                   for (action, key), rect in zip(options, rects)]
        return buttons

    def menu_action(self, action):
        if action in DIFFICULTIES:
            if self.state == "level_select":
                self.selected_difficulty = action
        elif action == "level_select":
            if self.state == "main_menu":
                self.state = "level_select"
        elif action in {f"level_{number}" for number in LEVELS}:
            if self.state == "level_select":
                self.start_session(self.selected_difficulty, int(action.removeprefix("level_")))
        elif action == "resume":
            self.resume()
        elif action == "restart":
            self.restart()
        elif action == "menu":
            self.to_menu()
        elif action == "quit":
            self.save_preferences()
            self.running = False
            self.clear_battle_resources()
        elif action == "settings":
            self.open_settings()
        elif self.state == "settings":
            if action in ("language_en", "language_zh-CN"):
                self.language = action.removeprefix("language_")
            elif action == "settings_back":
                self.close_settings()
                return
            elif action == "reset_keys":
                self.preferences.reset_keys()
            else:
                return
            self.editing_binding = None
            self.dragging_slider = None
            self.save_preferences()

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

    def activate_commands(self):
        # 共享键可触发多个动作，仍遵守武器互斥、能量和支援优先的规则。
        for command in sorted(self.commands, key=lambda c: c != "support"):
            if command == "support":
                self.try_support()
            elif self.weapons.try_activate(command, self.time):
                self.record("weapon_activate", kind=command)
        self.commands.clear()

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self.menu_action("quit")
            elif event.type == pygame.KEYDOWN:
                if getattr(event, "repeat", False):
                    continue
                if self.state == "settings":
                    if self.editing_binding is not None and valid_key(event.key):
                        self.preferences.bindings[self.editing_binding] = event.key
                        self.editing_binding = None
                        self.save_preferences()
                    elif self.editing_binding is None and event.key == pygame.K_ESCAPE:
                        self.close_settings()
                    continue
                if self.state == "main_menu" and event.key == pygame.K_RETURN:
                    self.menu_action("level_select")
                elif self.state == "level_select" and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.menu_action(f"level_{event.key - pygame.K_1 + 1}")
                elif self.state == "level_select" and event.key == pygame.K_RETURN:
                    self.menu_action(f"level_{self.level}")
                elif self.state == "playing":
                    fresh = event.key not in self.input.keys
                    self.input.keys.add(event.key)
                    if fresh:
                        for action in ("missile", "arc", "support"):
                            if event.key == self.preferences.bindings[action]:
                                self.commands.append(action)
                        if event.key == self.preferences.bindings["pause"]:
                            self.activate_commands()
                            self.pause()
                elif self.state == "paused" and event.key == self.preferences.bindings["pause"]:
                    self.resume()
                elif self.state == "level_select" and event.key == pygame.K_ESCAPE:
                    self.to_menu()
                elif self.state in ("defeat", "victory") and event.key == pygame.K_r:
                    self.restart()
            elif event.type == pygame.KEYUP:
                self.input.keys.discard(event.key)
            elif event.type == pygame.MOUSEMOTION:
                self.input.aim.update(event.pos)
                self.hover.update(event.pos)
                if self.state == "settings" and self.dragging_slider:
                    self.set_slider(self.dragging_slider, event.pos[0])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "playing":
                    self.input.fire = True
                    self.input.aim.update(event.pos)
                else:
                    if self.state == "settings":
                        self.editing_binding = None
                        for action, _, _, rect in self.control_rows():
                            if action in DEFAULT_BINDINGS and rect.collidepoint(event.pos):
                                self.editing_binding = action
                                break
                        if self.editing_binding is not None:
                            continue
                        for attribute, rect in self.sliders():
                            if rect.inflate(24, 24).collidepoint(event.pos):
                                self.dragging_slider = attribute
                                self.set_slider(attribute, event.pos[0])
                                break
                        if self.dragging_slider:
                            continue
                    for action, _, rect in self.buttons():
                        if rect.collidepoint(event.pos):
                            self.menu_action(action)
                            break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.input.fire = False
                if self.dragging_slider:
                    self.set_slider(self.dragging_slider, event.pos[0])
                    self.dragging_slider = None
                    self.save_preferences()
            elif event.type == pygame.WINDOWFOCUSLOST:
                if self.state == "playing":
                    self.pause()
                if self.dragging_slider:
                    self.dragging_slider = None
                    self.save_preferences()
                self.editing_binding = None
                self.input.clear()

    def update(self, dt: float) -> None:
        self.ui_time += max(0, dt)
        if not self.running or self.state != "playing":
            return
        self.weapons.expire(self.time)
        self.expire_support()
        # 同刻 X 先于伤害，避免已启动的支援仍收到当帧回能。
        self.activate_commands()
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

