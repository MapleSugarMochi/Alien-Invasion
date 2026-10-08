"""精灵、HUD、菜单与反馈；draw 不改变战斗生命或计时。"""
import math
import random
from pathlib import Path

import pygame
from pygame import Vector2

from settings import BACKGROUND, CYAN, HEIGHT, HUD_HEIGHT, WIDTH
from resources import Resources
from preferences import DEFAULT_BINDINGS
from art import (ARC, CORAL, HEALTH, ICE, INK, LINE, MISSILE, MUTED, PANEL,
                 PANEL_ACTIVE, PAPER, SLATE, corner_frame)


class Renderer:
    def __init__(self) -> None:
        self.font_path = pygame.font.match_font(["microsoftyahei", "simhei", "simsun"])
        # 系统字体索引可能把同家族的 Light 文件选为默认；优先使用常规字重。
        if self.font_path and Path(self.font_path).name.lower() == "msyhl.ttc":
            regular = Path(self.font_path).with_name("msyh.ttc")
            if regular.is_file():
                self.font_path = str(regular)
        self.font = pygame.font.Font(self.font_path, 20)
        self.large_font = pygame.font.Font(self.font_path, 40)
        self.small_font = pygame.font.Font(self.font_path, 16)
        self.resources = Resources()
        # 背景只缩放一次；等比覆盖逻辑画面，避免行星被拉成椭圆。
        source = self.resources.background
        factor = max(WIDTH / source.get_width(), HEIGHT / source.get_height())
        scaled = pygame.transform.smoothscale(source,
                    (round(source.get_width() * factor), round(source.get_height() * factor)))
        self.space = pygame.Surface((WIDTH, HEIGHT))
        self.space.blit(scaled, (0, 0))
        self.menu_space = self.space.copy()
        self.menu_space.fill((165, 175, 185), special_flags=pygame.BLEND_RGB_MULT)
        rng = random.Random(1)
        self.stars = [(rng.randrange(WIDTH), rng.randrange(HEIGHT), rng.uniform(4, 15),
                       rng.randrange(55, 105)) for _ in range(76)]
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((*INK, 220))

    def text(self, surface, message, pos, color=PAPER, anchor="topleft") -> None:
        rendered = self.font.render(message, True, color)
        surface.blit(rendered, rendered.get_rect(**{anchor: pos}))

    def label(self, surface, message, pos, color=MUTED, anchor="topleft"):
        rendered = self.small_font.render(message, True, color)
        surface.blit(rendered, rendered.get_rect(**{anchor: pos}))

    def sprite(self, surface, name, pos, angle=0):
        sprite = self.resources.sprite(name, angle)
        surface.blit(sprite, sprite.get_rect(center=pos))

    def feedback(self, game):
        self.resources.set_volumes(game.sfx_volume, game.music_volume)
        for sound in set(game.sound_events):
            self.resources.play(sound)
        game.sound_events.clear()
        if self.resources.audio_available:
            if game.state == "paused" or game.state == "settings" and game.settings_return_state == "paused":
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

    def draw(self, surface, game) -> None:
        tr = game.text
        menu = game.state in ("main_menu", "level_select", "settings")
        surface.blit(self.menu_space if menu else self.space, (0, 0))
        for x, y, speed, brightness in self.stars:
            pygame.draw.circle(surface, (brightness * 3 // 4, brightness * 9 // 10, brightness),
                               (x, int((y + (game.ui_time if menu else game.time) * speed) % HEIGHT)), 1)
        if game.state in ("main_menu", "level_select", "settings"):
            title = tr({"main_menu": "title", "level_select": "levels_title", "settings": "settings_title"}[game.state])
            heading = self.large_font.render(title, True, PAPER)
            surface.blit(heading, heading.get_rect(center=(640, 155 if game.state == "main_menu" else 70)))
            if game.state == "main_menu":
                self.sprite(surface, "player", Vector2(640, 290))
                self.text(surface, tr("tagline"), (640, 215), MUTED, anchor="midtop")
                pygame.draw.line(surface, LINE, (580, 348), (700, 348))
            elif game.state == "settings":
                self.draw_controls(surface, game)
                self.draw_settings(surface, game)
            else:
                self.text(surface, tr("level_hint"), (640, 135), MUTED, anchor="midtop")
                self.text(surface, tr("difficulty"), (350, 557), MUTED, anchor="topright")
            self.draw_buttons(surface, game)
            return
        for enemy in game.enemies:
            self.sprite(surface, enemy.kind, enemy.pos, 180)
        if game.boss and game.boss.hp > 0:
            boss = game.boss
            self.sprite(surface, "boss", boss.pos, 180)
            pygame.draw.rect(surface, SLATE, (455, 99, 370, 4))
            pygame.draw.rect(surface, CORAL, (455, 99, int(370 * boss.hp / boss.max_hp), 4))
            self.label(surface, tr("boss_status", hp=boss.hp, max_hp=boss.max_hp, phase=boss.phase),
                       (640, 73), PAPER, anchor="midtop")
            if boss.warning(game.time):
                pygame.draw.circle(surface, CORAL, boss.pos + Vector2(0, 40), 12, 2)
            if boss.transition_until:
                self.text(surface, tr("phase_transition"), (640, 250), anchor="midtop")
        if game.phase == "boss_warning":
            self.text(surface, tr("boss_warning"), (640, 300), CORAL, anchor="midtop")
        for meteor in game.meteors:
            self.sprite(surface, "meteor_small" if meteor.radius == 22 else "meteor_large", meteor.pos, meteor.angle)
        for projectile in game.projectiles + game.enemy_bullets:
            self.draw_projectile(surface, projectile)
        for until, pos, radius in game.effects:
            self.draw_impact(surface, pos, radius, max(0, until - game.time))
        for until, points in game.arc_effects:
            # 时间与端点决定折线，不使用游戏随机源，也不改变真实链路。
            bolts = [Vector2(points[0])]
            for index, (start, end) in enumerate(zip(points, points[1:])):
                start, end = Vector2(start), Vector2(end)
                side = (end - start).rotate(90)
                if side.length_squared():
                    side.scale_to_length(4 if index % 2 else -4)
                bolts.extend((start.lerp(end, .35) + side, start.lerp(end, .7) - side, end))
            if len(bolts) > 1:
                pygame.draw.lines(surface, ARC, False, bolts, 2)
                pygame.draw.aalines(surface, PAPER, False, bolts)
        targets = {t.id: t for t in game.targets}
        for round_ in game.support.rounds:
            if round_.hit:
                continue
            for target_id in round_.ids:
                target = targets.get(target_id)
                if not target:
                    continue
                progress = max(0, min(1, (game.time - round_.start) / .4))
                radius = target.radius + 22 - progress * 14
                rect = pygame.Rect(0, 0, radius * 2, radius * 2)
                rect.center = target.pos
                corner_frame(surface, PAPER, rect, 10, 1)
                if round_.launched:
                    flight = max(0, min(1, (game.time - round_.start - .4) / .25))
                    pos = Vector2(WIDTH + 40, 110).lerp(target.pos, flight)
                    pygame.draw.line(surface, ICE, pos, pos - Vector2(28, -12), 3)
                    pygame.draw.aaline(surface, PAPER, pos, pos - Vector2(22, -9))
        for pickup in game.pickups:
            self.sprite(surface, pickup.kind, pickup.pos)
        if game.meteor_warning:
            _, x, _ = game.meteor_warning
            pygame.draw.polygon(surface, MISSILE, [(x - 9, 116), (x + 9, 116), (x, 130)], 1)
        if game.time >= game.player.invulnerable_until or int(game.time * 18) % 2:
            tail = game.player.pos - game.player.direction * 24
            end = tail - game.player.direction * (10 + 3 * math.sin(game.time * 35))
            pygame.draw.line(surface, ICE, tail, end, 3)
            pygame.draw.aaline(surface, PAPER, tail, end)
            self.sprite(surface, "player", game.player.pos, Vector2(0, -1).angle_to(game.player.direction) * -1)
            # 核心亮环对应真实碰撞半径，宽翼与尾焰不扩大碰撞。
            pygame.draw.circle(surface, (91, 126, 139), game.player.pos, game.player.radius, 1)
        self.draw_hud(surface, game)
        phase_key = "boss_approach" if game.phase == "boss_warning" else game.phase
        if game.tutorial:
            self.text(surface, tr("tutorial_status", step=game.tutorial.step,
                                 title=tr(f"tutorial_title_{game.tutorial.step}")), (24, 83))
            self.text(surface, tr("tutorial_label"), (WIDTH - 24, 82), anchor="topright")
        else:
            self.text(surface, tr("wave_status", level=game.level, number=game.wave.number, phase=tr(phase_key)), (24, 83))
            self.text(surface, tr(game.difficulty.id), (WIDTH - 24, 82), anchor="topright")
        aim = game.input.display_aim
        for offset in (-1, 1):
            pygame.draw.line(surface, PAPER, aim + Vector2(offset * 5, 0), aim + Vector2(offset * 11, 0))
            pygame.draw.line(surface, PAPER, aim + Vector2(0, offset * 5), aim + Vector2(0, offset * 11))
        if game.tutorial and game.state == "playing":
            self.draw_tutorial(surface, game)
            self.draw_buttons(surface, game)
        if game.state != "playing":
            surface.blit(self.overlay, (0, 0))
            if game.state == "paused":
                self.text(surface, tr("paused", binding=game.binding_name("pause")), (640, 280), anchor="midtop")
            elif game.state == "tutorial_complete":
                self.text(surface, tr("tutorial_complete"), (640, 110), CYAN, anchor="midtop")
                for index in range(8):
                    self.text(surface, f"[OK] {tr(f'tutorial_title_{index + 1}')}",
                              (210 + (index // 4) * 520, 170 + (index % 4) * 33))
                self.text(surface, tr("tutorial_summary", seconds=game.time, count=game.tutorial.retries),
                          (640, 325), anchor="midtop")
            elif game.state == "tutorial_retry":
                self.text(surface, tr("tutorial_retry"), (640, 280), anchor="midtop")
                self.text(surface, tr(f"tutorial_title_{game.tutorial.step}"), (640, 330), anchor="midtop")
            else:
                self.text(surface, tr(game.state), (640, 255), anchor="midtop")
                self.text(surface, tr("result", score=game.score, kills=game.kills, seconds=game.time), (640, 330), anchor="midtop")
            self.draw_buttons(surface, game)

    def draw_hud(self, surface, game):
        tr = game.text
        pygame.draw.rect(surface, INK, (0, 0, WIDTH, HUD_HEIGHT))
        pygame.draw.line(surface, (26, 36, 45), (24, 63), (WIDTH - 24, 63))
        self.text(surface, tr("hp_score", hp=game.player.hp, score=game.score), (24, 10))
        pygame.draw.rect(surface, SLATE, (24, 46, 214, 3))
        pygame.draw.rect(surface, CORAL if game.player.hp <= 25 else ICE,
                         (24, 46, round(214 * game.player.hp / 100), 3))
        weapon = (tr("bullet") if game.weapons.active == "bullet" else
                  tr("weapon_status", weapon=tr(game.weapons.active),
                     seconds=max(0, game.weapons.active_until - game.time)))
        self.text(surface, weapon, (277, 10), PAPER)
        self.label(surface, tr("action_fire"), (277, 37), MUTED)
        for index, kind in enumerate(("missile", "arc")):
            x = 600 + 210 * index
            image = self.resources.scaled(kind, (30, 30))
            surface.blit(image, image.get_rect(center=(x + 17, 25)))
            color = (CORAL if game.weapons.failed_until[kind] > game.time else
                     ICE if game.weapons.charges[kind] == 3 else PAPER)
            self.text(surface, game.binding_name(kind), (x + 46, 8), color)
            for charge in range(3):
                rect = pygame.Rect(x + 47 + charge * 13, 41, 5, 10)
                pygame.draw.rect(surface, color if charge < game.weapons.charges[kind] else SLATE, rect)
            if game.weapons.active == kind:
                pygame.draw.line(surface, ICE, (x, 58), (x + 185, 58))
        image = self.resources.scaled("support", (30, 30))
        surface.blit(image, image.get_rect(center=(1027, 25)))
        color = CORAL if game.support.failed_until > game.time else ICE if game.energy_units == 1000 else PAPER
        message = (f"{game.binding_name('support')}  {game.energy_units // 10}%" if not game.support.active else
                   tr("support_status", seconds=max(0, game.support.end_at - game.time)))
        self.text(surface, message, (1054, 8), color)
        pygame.draw.rect(surface, SLATE, (1054, 45, 195, 3))
        amount = (max(0, game.support.end_at - game.time) / 7.5 if game.support.active else game.energy_units / 1000)
        pygame.draw.rect(surface, ICE, (1054, 45, round(195 * amount), 3))

    @staticmethod
    def draw_projectile(surface, projectile):
        color = CORAL if projectile.source == "enemy" else MISSILE if projectile.source == "missile" else ICE
        direction = projectile.velocity.normalize() if projectile.velocity.length_squared() else Vector2(0, -1)
        tail = projectile.pos - direction * (12 if projectile.source == "missile" else 7)
        # 暗外缘表达实际弹丸宽度；明亮核心短而清晰，避免整条弹道泛光。
        edge = tuple(round(value * .45) for value in color)
        pygame.draw.line(surface, edge, tail, projectile.pos, projectile.radius * 2)
        pygame.draw.line(surface, color, tail, projectile.pos, max(2, projectile.radius))
        pygame.draw.aaline(surface, PAPER if projectile.source != "enemy" else (243, 200, 188), tail, projectile.pos)

    @staticmethod
    def draw_impact(surface, pos, radius, remaining):
        duration = .18 if radius <= 12 else .35 if radius == 70 else .4
        progress = max(0, min(1, 1 - remaining / duration))
        reach = max(4, round(radius * (.22 + .65 * progress)))
        fade = 1 - progress
        color = tuple(round(value * (.35 + .65 * fade)) for value in CORAL)
        if radius > 12:
            pygame.draw.circle(surface, LINE, pos, reach, 1)
        for index in range(6 if radius <= 12 else 9):
            direction = Vector2(0, -1).rotate(index * 137.5)
            start = Vector2(pos) + direction * reach * .65
            pygame.draw.aaline(surface, color, start, Vector2(pos) + direction * reach)
        if progress < .6:
            pygame.draw.circle(surface, PAPER, pos, max(1, round(3 * fade)))

    def draw_buttons(self, surface, game):
        for action, label, rect in game.buttons():
            active = (game.state == "level_select" and action == game.selected_difficulty or
                      action == "language_" + game.language or rect.collidepoint(game.hover))
            pygame.draw.rect(surface, PANEL_ACTIVE if active else PANEL, rect, border_radius=4)
            pygame.draw.rect(surface, ICE if active else LINE, rect, 1, border_radius=4)
            if active:
                pygame.draw.line(surface, ICE, (rect.left + 1, rect.top + 12),
                                 (rect.left + 1, rect.bottom - 12), 2)
            if game.state == "level_select" and action.startswith("level_"):
                number = int(action.removeprefix("level_"))
                heading = self.large_font.render(f"{number:02}", True, PAPER if active else MUTED)
                surface.blit(heading, heading.get_rect(center=(rect.centerx, rect.top + 55)))
                if number == 1:
                    self.sprite(surface, "player", (rect.centerx, rect.top + 135))
                elif number == 2:
                    self.sprite(surface, "scout", (rect.centerx - 42, rect.top + 140), 180)
                    self.sprite(surface, "shooter", (rect.centerx + 36, rect.top + 140), 180)
                else:
                    image = self.resources.scaled("boss", (180, 90))
                    surface.blit(image, image.get_rect(center=(rect.centerx, rect.top + 135)))
                self.text(surface, label, (rect.centerx, rect.top + 180), anchor="midtop")
                self.text(surface, game.text("tutorial_label" if number == 1 else f"level_{number}_note"),
                          (rect.centerx, rect.top + 210), MUTED, anchor="midtop")
                entry = pygame.Rect(rect.left + 24, rect.bottom - 68, rect.width - 48, 44)
                pygame.draw.line(surface, ICE if active else LINE,
                                 (entry.left, entry.top), (entry.right, entry.top))
                self.text(surface, game.text("enter_level"), entry.center, ICE if active else PAPER, anchor="center")
                continue
            text = self.font.render(label, True, PAPER if active else MUTED)
            surface.blit(text, text.get_rect(center=rect.center))

    def wrapped_text(self, surface, message, rect, color=PAPER):
        """按字宽换行，兼容中文与较长的自定义键位名；所有行仍走统一 text 接口。"""
        lines, current = [], ""
        for word in message.split(" "):
            candidate = current + (" " if current else "") + word
            if self.font.size(candidate)[0] <= rect.width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            for char in word:
                if self.font.size(current + char)[0] > rect.width:
                    lines.append(current)
                    current = ""
                current += char
        if current:
            lines.append(current)
        for index, line in enumerate(lines):
            if (index + 1) * 26 <= rect.height:
                self.text(surface, line, (rect.x, rect.y + index * 26), color)
        return len(lines) * 26

    def draw_tutorial(self, surface, game):
        tutorial, tr = game.tutorial, game.text
        panel = pygame.Rect(24, 118, 970, 120)
        pygame.draw.rect(surface, PANEL, panel, border_radius=4)
        pygame.draw.rect(surface, LINE, panel, 1, border_radius=4)
        pygame.draw.line(surface, ICE, (panel.left, panel.top + 12), (panel.left, panel.bottom - 12), 2)
        y = panel.y + 10
        for line in tutorial.lines(game):
            used = self.wrapped_text(surface, line, pygame.Rect(panel.x + 14, y, panel.width - 28, panel.bottom - y))
            y += used + 4
        for enemy in game.enemies:
            if enemy.training:
                pygame.draw.circle(surface, MISSILE, enemy.pos, enemy.radius + 6, 1)
        if tutorial.step == 2 and not tutorial.aim_seen:
            pygame.draw.circle(surface, CYAN, tutorial.aim_target, 25, 2)
        for pickup in game.pickups:
            start = pickup.pos + Vector2(0, -54)
            end = pickup.pos + Vector2(0, -28)
            pygame.draw.line(surface, CYAN, start, end, 2)
            pygame.draw.lines(surface, CYAN, False, [end + Vector2(-6, -7), end, end + Vector2(6, -7)], 2)
        if tutorial.step == 3:
            x = game.meteor_warning[1] if game.meteor_warning else tutorial.meteor.pos.x if tutorial.meteor else None
            if x is not None:
                pygame.draw.rect(surface, (119, 82, 74), (x - 36, 245, 72, HEIGHT - 245), 1)
        if tutorial.step == 6:
            pygame.draw.circle(surface, LINE, (640, 500), 40, 1)
            if game.time - tutorial.progress_at >= 30:
                pygame.draw.circle(surface, LINE, game.player.pos, 300, 1)
        if game.time - tutorial.progress_at >= 30:
            # 停留较久时给出屏幕内方向辅助；不替玩家移动或判定通过。
            destination = game.pickups[0].pos if game.pickups else None
            if destination is None and tutorial.step in (2, 5, 6, 7):
                destination = (Vector2(640, 500) if tutorial.step == 6 else
                               game.enemies[0].pos if game.enemies else tutorial.aim_target)
            if destination is None and tutorial.step == 3 and x is not None:
                destination = Vector2(max(80, x - 180) if x > WIDTH / 2 else min(WIDTH - 80, x + 180), game.player.pos.y)
            if destination is not None:
                direction = destination - game.player.pos
                if direction.length_squared() > 1:
                    direction = direction.normalize()
                    start = game.player.pos + direction * 34
                    end = start + direction * 58
                    side = direction.rotate(90) * 7
                    pygame.draw.line(surface, CYAN, start, end, 2)
                    pygame.draw.lines(surface, CYAN, False, [end - direction * 12 + side, end, end - direction * 12 - side], 2)
        if tutorial.step in (5, 6, 7):
            x = {5: 600, 6: 810, 7: 1010}[tutorial.step]
            corner_frame(surface, ICE, (x - 5, 3, 195 if tutorial.step < 7 else 260, 56), 8)
        conflicting = any(game.preferences.bindings[a] == game.preferences.bindings[b]
                          for a, b in (("move_up", "move_down"), ("move_left", "move_right")))
        notice = "tutorial_conflict" if conflicting else tutorial.notice
        if tutorial.step > 1 and not tutorial.transitioning and game.time - tutorial.progress_at >= 15:
            notice = f"tutorial_help_{tutorial.step}" if not conflicting else notice
        keys = {action: game.binding_name(action) for action in game.preferences.bindings}
        self.wrapped_text(surface, tr(notice, **keys) if notice else "", pygame.Rect(24, 628, 1232, 52), CYAN)
        self.text(surface, tr("tutorial_pause_hint", binding=game.binding_name("pause")), (24, 686))

    def draw_controls(self, surface, game):
        pygame.draw.rect(surface, PANEL_ACTIVE, (80, 132, 550, 38))
        self.text(surface, game.text("action_header"), (98, 138), PAPER)
        self.text(surface, game.text("key_header"), (505, 138), PAPER, anchor="midtop")
        conflicts = game.preferences.conflicts()
        for action, label, key, rect in game.control_rows():
            pygame.draw.rect(surface, PANEL, (80, rect.y, 300, rect.height))
            editable = game.state == "settings" and action in DEFAULT_BINDINGS
            selected = game.editing_binding == action
            pygame.draw.rect(surface, PANEL_ACTIVE if selected or editable and rect.collidepoint(game.hover) else PANEL, rect)
            pygame.draw.rect(surface, ICE if selected else LINE, rect, 1)
            pygame.draw.rect(surface, LINE, (80, rect.y, 300, rect.height), 1)
            if action in conflicts:
                # 四秒一轮，红色覆盖仅 7–13% 不透明度，避免刺眼闪烁。
                alpha = round(18 + 14 * (1 - math.cos(math.tau * game.ui_time / 4)) / 2)
                tint = pygame.Surface(rect.size, pygame.SRCALPHA)
                tint.fill((235, 74, 88, alpha))
                pygame.draw.rect(tint, (235, 74, 88, alpha + 32), tint.get_rect(), 2)
                surface.blit(tint, rect)
            self.text(surface, label, (98, rect.y + 5))
            self.text(surface, game.text("key_prompt") if selected else key, (rect.centerx, rect.y + 5), anchor="midtop")
        self.text(surface, game.text("edit_hint"), (80, 570))

    def draw_settings(self, surface, game):
        pygame.draw.rect(surface, PANEL, (670, 132, 550, 420), border_radius=4)
        pygame.draw.rect(surface, LINE, (670, 132, 550, 420), 1, border_radius=4)
        self.text(surface, game.text("language"), (720, 160), PAPER)
        for attribute, rect in game.sliders():
            self.text(surface, game.text(attribute), (720, rect.y - 38))
            value = getattr(game, attribute)
            self.text(surface, f"{round(value * 100)}%", (1160, rect.y - 38), anchor="topright")
            pygame.draw.line(surface, SLATE, (rect.left, rect.centery), (rect.right, rect.centery), 3)
            x = round(rect.left + value * rect.width)
            pygame.draw.line(surface, ICE, (rect.left, rect.centery), (x, rect.centery), 3)
            pygame.draw.circle(surface, PAPER, (x, rect.centery), 6)
        self.text(surface, game.text("bgm_loaded" if self.resources.music_file else "bgm_missing"), (700, 485), MUTED)
        if not self.resources.audio_available:
            self.text(surface, game.text("audio_unavailable"), (700, 515))
        if game.preferences.conflicts():
            self.text(surface, game.text("conflict_hint"), (700, 565), (200, 154, 158))
        if game.save_failed:
            self.text(surface, game.text("save_failed"), (700, 595), (200, 154, 158))

