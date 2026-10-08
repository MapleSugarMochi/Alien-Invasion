"""精灵、HUD、菜单与反馈；draw 不改变战斗生命或计时。"""
import math
import random

import pygame
from pygame import Vector2

from settings import BACKGROUND, CYAN, HEIGHT, HUD_HEIGHT, WIDTH
from resources import Resources
from preferences import DEFAULT_BINDINGS


class Renderer:
    def __init__(self) -> None:
        self.font_path = pygame.font.match_font(["microsoftyahei", "simhei", "simsun"])
        self.font = pygame.font.Font(self.font_path, 20)
        self.large_font = pygame.font.Font(self.font_path, 42)
        self.resources = Resources()
        rng = random.Random(1)
        self.stars = [(rng.randrange(WIDTH), rng.randrange(HEIGHT), rng.uniform(15, 65))
                      for _ in range(160)]

    def text(self, surface, message, pos, color=(205, 222, 237), anchor="topleft") -> None:
        rendered = self.font.render(message, True, color)
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
        surface.fill(BACKGROUND)
        for x, y, speed in self.stars:
            pygame.draw.circle(surface, (90, 120, 153), (x, int((y + game.time * speed) % HEIGHT)), 1)
        if game.state in ("main_menu", "level_select", "settings"):
            title = tr({"main_menu": "title", "level_select": "levels_title", "settings": "settings_title"}[game.state])
            heading = self.large_font.render(title, True, CYAN)
            surface.blit(heading, heading.get_rect(center=(640, 155 if game.state == "main_menu" else 70)))
            if game.state == "main_menu":
                self.sprite(surface, "player", Vector2(640, 290))
                self.text(surface, tr("tagline"), (640, 205), anchor="midtop")
            elif game.state == "settings":
                self.draw_controls(surface, game)
                self.draw_settings(surface, game)
            else:
                self.text(surface, tr("level_hint"), (640, 135), anchor="midtop")
                self.text(surface, tr("difficulty"), (350, 557), CYAN, anchor="topright")
            self.draw_buttons(surface, game)
            return
        for enemy in game.enemies:
            self.sprite(surface, enemy.kind, enemy.pos, 180)
        if game.boss and game.boss.hp > 0:
            boss = game.boss
            self.sprite(surface, "boss", boss.pos, 180)
            pygame.draw.rect(surface, (35, 29, 60), (320, 100, 640, 12))
            pygame.draw.rect(surface, (186, 130, 244), (320, 100, int(640 * boss.hp / boss.max_hp), 12))
            self.text(surface, tr("boss_status", hp=boss.hp, max_hp=boss.max_hp, phase=boss.phase), (640, 78), anchor="midtop")
            if boss.warning(game.time):
                pygame.draw.circle(surface, (255, 112, 88), boss.pos + Vector2(0, 40), 15, 3)
            if boss.transition_until:
                self.text(surface, tr("phase_transition"), (640, 250), anchor="midtop")
        if game.phase == "boss_warning":
            self.text(surface, tr("boss_warning"), (640, 300), (255, 112, 88), anchor="midtop")
        for meteor in game.meteors:
            self.sprite(surface, "meteor_small" if meteor.radius == 22 else "meteor_large", meteor.pos, meteor.angle)
        for projectile in game.projectiles + game.enemy_bullets:
            color = (255, 112, 88) if projectile.source == "enemy" else ((255, 184, 77) if projectile.source == "missile" else CYAN)
            pygame.draw.line(surface, color, projectile.pos - projectile.velocity.normalize() * 9 if projectile.velocity.length_squared() else projectile.pos,
                             projectile.pos, projectile.radius * 2)
        for until, pos, radius in game.effects:
            pygame.draw.circle(surface, (255, 205, 132), pos, radius, 1)
            effect = pygame.transform.smoothscale(self.resources.images["explosion"], (min(100, radius * 2), min(100, radius * 2)))
            effect.set_alpha(155)
            surface.blit(effect, effect.get_rect(center=pos))
        for until, points in game.arc_effects:
            pygame.draw.lines(surface, (180, 147, 255), False, points, 3)
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
                pygame.draw.rect(surface, (255, 209, 105), rect, 2)
                if round_.launched:
                    flight = max(0, min(1, (game.time - round_.start - .4) / .25))
                    pos = Vector2(WIDTH + 40, 110).lerp(target.pos, flight)
                    pygame.draw.line(surface, (255, 209, 105), pos, pos - Vector2(35, -15), 4)
        for pickup in game.pickups:
            self.sprite(surface, pickup.kind, pickup.pos)
        if game.meteor_warning:
            _, x, _ = game.meteor_warning
            pygame.draw.polygon(surface, (255, 184, 77), [(x - 12, 72), (x + 12, 72), (x, 91)], 2)
        if game.time >= game.player.invulnerable_until or int(game.time * 18) % 2:
            tail = game.player.pos - game.player.direction * 24
            pygame.draw.line(surface, (30, 131, 183), tail, tail - game.player.direction * (12 + 5 * math.sin(game.time * 35)), 5)
            self.sprite(surface, "player", game.player.pos, Vector2(0, -1).angle_to(game.player.direction) * -1)
            # 核心亮环对应真实碰撞半径，宽翼与尾焰不扩大碰撞。
            pygame.draw.circle(surface, (61, 148, 183), game.player.pos, game.player.radius, 1)
        pygame.draw.rect(surface, (13, 24, 42), (0, 0, WIDTH, HUD_HEIGHT))
        self.text(surface, tr("hp_score", hp=game.player.hp, score=game.score), (24, 21))
        self.text(surface, tr("weapon_status", weapon=tr(game.weapons.active), seconds=max(0, game.weapons.active_until-game.time)), (300, 21))
        for index, kind in enumerate(("missile", "arc")):
            color = (255, 112, 88) if game.weapons.failed_until[kind] > game.time else (CYAN if game.weapons.charges[kind] == 3 else (140, 165, 187))
            self.sprite(surface, kind, (620 + 210 * index, 32))
            self.text(surface, f"{game.binding_name(kind)} {'■' * game.weapons.charges[kind]}{'□' * (3 - game.weapons.charges[kind])}", (650 + 210 * index, 21), color)
        color = (255, 112, 88) if game.support.failed_until > game.time else (CYAN if game.energy_units == 1000 else (140, 165, 187))
        self.text(surface, f"{game.binding_name('support')}  {game.energy_units // 10}%" if not game.support.active else tr("support_status", seconds=game.support.end_at - game.time), (1070, 21), color)
        self.sprite(surface, "support", (1030, 32))
        pygame.draw.rect(surface, (23, 46, 66), (24, 52, 200, 4))
        pygame.draw.rect(surface, (117, 237, 158), (24, 52, game.player.hp * 2, 4))
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
            pygame.draw.line(surface, CYAN, aim + Vector2(offset * 5, 0), aim + Vector2(offset * 13, 0))
            pygame.draw.line(surface, CYAN, aim + Vector2(0, offset * 5), aim + Vector2(0, offset * 13))
        if game.tutorial and game.state == "playing":
            self.draw_tutorial(surface, game)
            self.draw_buttons(surface, game)
        if game.state != "playing":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((3, 8, 20, 190))
            surface.blit(overlay, (0, 0))
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

    def draw_buttons(self, surface, game):
        for action, label, rect in game.buttons():
            active = (game.state == "level_select" and action == game.selected_difficulty or
                      action == "language_" + game.language or rect.collidepoint(game.hover))
            pygame.draw.rect(surface, (24, 63, 80) if active else (17, 33, 52), rect, border_radius=8)
            pygame.draw.rect(surface, CYAN if active else (63, 94, 113), rect, 2, border_radius=8)
            if game.state == "level_select" and action.startswith("level_"):
                number = int(action.removeprefix("level_"))
                heading = self.large_font.render(f"{number:02}", True, CYAN)
                surface.blit(heading, heading.get_rect(center=(rect.centerx, rect.top + 55)))
                self.sprite(surface, "player", (rect.centerx, rect.top + 140))
                self.text(surface, label, (rect.centerx, rect.top + 180), anchor="midtop")
                self.text(surface, game.text("tutorial_label" if number == 1 else f"level_{number}_note"),
                          (rect.centerx, rect.top + 210), anchor="midtop")
                entry = pygame.Rect(rect.left + 24, rect.bottom - 68, rect.width - 48, 44)
                pygame.draw.rect(surface, (28, 73, 90) if active else (24, 47, 65), entry, border_radius=6)
                self.text(surface, game.text("enter_level"), entry.center, CYAN, anchor="center")
                continue
            text = self.font.render(label, True, CYAN if active else (205, 222, 237))
            surface.blit(text, text.get_rect(center=rect.center))

    def wrapped_text(self, surface, message, rect, color=(205, 222, 237)):
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
        pygame.draw.rect(surface, (13, 26, 43), panel, border_radius=10)
        y = panel.y + 10
        for line in tutorial.lines(game):
            used = self.wrapped_text(surface, line, pygame.Rect(panel.x + 14, y, panel.width - 28, panel.bottom - y))
            y += used + 4
        for enemy in game.enemies:
            if enemy.training:
                pygame.draw.circle(surface, (229, 196, 118), enemy.pos, enemy.radius + 6, 1)
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
                pygame.draw.rect(surface, (159, 91, 53), (x - 36, 245, 72, HEIGHT - 245), 1)
        if tutorial.step == 6:
            pygame.draw.circle(surface, (61, 148, 183), (640, 500), 40, 1)
            if game.time - tutorial.progress_at >= 30:
                pygame.draw.circle(surface, (61, 148, 183), game.player.pos, 300, 1)
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
            pygame.draw.rect(surface, CYAN, (x, 3, 195 if tutorial.step < 7 else 260, 56), 1, border_radius=6)
        conflicting = any(game.preferences.bindings[a] == game.preferences.bindings[b]
                          for a, b in (("move_up", "move_down"), ("move_left", "move_right")))
        notice = "tutorial_conflict" if conflicting else tutorial.notice
        if tutorial.step > 1 and not tutorial.transitioning and game.time - tutorial.progress_at >= 15:
            notice = f"tutorial_help_{tutorial.step}" if not conflicting else notice
        keys = {action: game.binding_name(action) for action in game.preferences.bindings}
        self.wrapped_text(surface, tr(notice, **keys) if notice else "", pygame.Rect(24, 628, 1232, 52), CYAN)
        self.text(surface, tr("tutorial_pause_hint", binding=game.binding_name("pause")), (24, 686))

    def draw_controls(self, surface, game):
        pygame.draw.rect(surface, (17, 33, 52), (80, 132, 550, 38))
        self.text(surface, game.text("action_header"), (98, 138), CYAN)
        self.text(surface, game.text("key_header"), (505, 138), CYAN, anchor="midtop")
        conflicts = game.preferences.conflicts()
        for action, label, key, rect in game.control_rows():
            pygame.draw.rect(surface, (13, 26, 43), (80, rect.y, 300, rect.height))
            editable = game.state == "settings" and action in DEFAULT_BINDINGS
            selected = game.editing_binding == action
            pygame.draw.rect(surface, (24, 63, 80) if selected or editable and rect.collidepoint(game.hover) else (17, 33, 52), rect)
            pygame.draw.rect(surface, CYAN if selected else (45, 67, 85), rect, 1)
            pygame.draw.rect(surface, (45, 67, 85), (80, rect.y, 300, rect.height), 1)
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
        pygame.draw.rect(surface, (13, 26, 43), (670, 132, 550, 420), border_radius=12)
        self.text(surface, game.text("language"), (720, 160), CYAN)
        for attribute, rect in game.sliders():
            self.text(surface, game.text(attribute), (720, rect.y - 38))
            value = getattr(game, attribute)
            self.text(surface, f"{round(value * 100)}%", (1160, rect.y - 38), anchor="topright")
            pygame.draw.line(surface, (45, 67, 85), (rect.left, rect.centery), (rect.right, rect.centery), 6)
            x = round(rect.left + value * rect.width)
            pygame.draw.line(surface, CYAN, (rect.left, rect.centery), (x, rect.centery), 6)
            pygame.draw.circle(surface, (205, 222, 237), (x, rect.centery), 10)
        self.text(surface, game.text("bgm_loaded" if self.resources.music_file else "bgm_missing"), (700, 485))
        if not self.resources.audio_available:
            self.text(surface, game.text("audio_unavailable"), (700, 515))
        if game.preferences.conflicts():
            self.text(surface, game.text("conflict_hint"), (700, 565), (200, 154, 158))
        if game.save_failed:
            self.text(surface, game.text("save_failed"), (700, 595), (200, 154, 158))

