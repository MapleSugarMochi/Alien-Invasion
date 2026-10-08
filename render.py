"""精灵、HUD、菜单与反馈；draw 不改变战斗生命或计时。"""
import math
import random

import pygame
from pygame import Vector2

from settings import BACKGROUND, CYAN, HEIGHT, HUD_HEIGHT, WIDTH
from resources import Resources


class Renderer:
    def __init__(self) -> None:
        self.font_path = pygame.font.match_font(["microsoftyahei", "simhei", "simsun"])
        self.font = pygame.font.Font(self.font_path, 20)
        self.large_font = pygame.font.Font(self.font_path, 42)
        self.resources = Resources()
        rng = random.Random(1)
        self.stars = [(rng.randrange(WIDTH), rng.randrange(HEIGHT), rng.uniform(15, 65))
                      for _ in range(160)]

    def text(self, surface, message, pos, color=(205, 222, 237)) -> None:
        surface.blit(self.font.render(message, True, color), pos)

    def sprite(self, surface, name, pos, angle=0):
        sprite = self.resources.sprite(name, angle)
        surface.blit(sprite, sprite.get_rect(center=pos))

    def feedback(self, game):
        self.resources.set_volumes(game.sfx_volume, game.music_volume)
        for sound in set(game.sound_events):
            self.resources.play(sound)
        game.sound_events.clear()
        if self.resources.audio_available:
            if game.state in ("paused", "audio"):
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()

    def draw(self, surface, game) -> None:
        surface.fill(BACKGROUND)
        for x, y, speed in self.stars:
            pygame.draw.circle(surface, (90, 120, 153), (x, int((y + game.time * speed) % HEIGHT)), 1)
        if game.state in ("main_menu", "setup", "audio"):
            title = {"main_menu": "ALIEN INVASION", "setup": "出击准备", "audio": "声音设置"}[game.state]
            heading = self.large_font.render(title, True, CYAN)
            surface.blit(heading, heading.get_rect(center=(640, 155)))
            if game.state == "main_menu":
                self.sprite(surface, "player", Vector2(640, 290))
                self.text(surface, "生存 · 12 波敌群 · 外星母舰", (475, 205))
            elif game.state == "audio":
                self.text(surface, f"音效 {round(game.sfx_volume * 100)}%    音乐 {round(game.music_volume * 100)}%", (475, 255))
                status = "已载入 BGM" if self.resources.music_file else "尚未提供 BGM，当前无音乐运行"
                self.text(surface, status, (455, 300))
                if not self.resources.audio_available:
                    self.text(surface, "音频设备不可用：静音运行", (465, 330))
            else:
                instructions = ["WASD 按屏幕方向移动，鼠标瞄准，按住左键持续射击",
                                "Esc 暂停／继续；窗口失焦自动暂停，继续后重新按左键",
                                "每 7 秒等概率回血／导弹／电弧补给；满容量不消耗",
                                "完成 12 波并击毁母舰获胜；生命归零失败；重开清空本局",
                                "Q 导弹 / E 电弧：三格充满后替换武器 5 秒，仍需左键",
                                "X 满能量呼叫五轮支援；支援中不回能；1/2/3 选难度"]
                for index, line in enumerate(instructions):
                    self.text(surface, line, (305, 225 + index * 36))
            self.draw_buttons(surface, game)
            return
        for enemy in game.enemies:
            self.sprite(surface, enemy.kind, enemy.pos, 180)
        if game.boss and game.boss.hp > 0:
            boss = game.boss
            self.sprite(surface, "boss", boss.pos, 180)
            pygame.draw.rect(surface, (35, 29, 60), (320, 100, 640, 12))
            pygame.draw.rect(surface, (186, 130, 244), (320, 100, int(640 * boss.hp / boss.max_hp), 12))
            self.text(surface, f"MOTHERSHIP  {boss.hp}/{boss.max_hp}  PHASE {boss.phase}", (465, 78))
            if boss.warning(game.time):
                pygame.draw.circle(surface, (255, 112, 88), boss.pos + Vector2(0, 40), 15, 3)
            if boss.transition_until:
                self.text(surface, "PHASE TRANSITION", (530, 250))
        if game.phase == "boss_warning":
            self.text(surface, "WARNING — MOTHERSHIP APPROACHING", (425, 300), (255, 112, 88))
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
        self.text(surface, f"HP {game.player.hp:3}  分数 {game.score}", (24, 21))
        weapon_name = {"bullet": "基础子弹", "missile": "追踪导弹", "arc": "连锁电弧"}[game.weapons.active]
        self.text(surface, f"{weapon_name}  {max(0, game.weapons.active_until-game.time):.1f}s", (300, 21))
        for index, kind in enumerate(("missile", "arc")):
            color = (255, 112, 88) if game.weapons.failed_until[kind] > game.time else (CYAN if game.weapons.charges[kind] == 3 else (140, 165, 187))
            self.sprite(surface, kind, (620 + 210 * index, 32))
            self.text(surface, f"{'Q' if index == 0 else 'E'} {'■' * game.weapons.charges[kind]}{'□' * (3 - game.weapons.charges[kind])}", (650 + 210 * index, 21), color)
        color = (255, 112, 88) if game.support.failed_until > game.time else (CYAN if game.energy_units == 1000 else (140, 165, 187))
        self.text(surface, f"X  {game.energy_units // 10}%" if not game.support.active else f"支援 {game.support.end_at - game.time:.1f}s", (1070, 21), color)
        self.sprite(surface, "support", (1030, 32))
        pygame.draw.rect(surface, (23, 46, 66), (24, 52, 200, 4))
        pygame.draw.rect(surface, (117, 237, 158), (24, 52, game.player.hp * 2, 4))
        self.text(surface, f"WAVE {game.wave.number}/12   {game.phase.upper()}", (24, 83))
        self.text(surface, game.difficulty.label, (1190, 82))
        aim = game.input.display_aim
        for offset in (-1, 1):
            pygame.draw.line(surface, CYAN, aim + Vector2(offset * 5, 0), aim + Vector2(offset * 13, 0))
            pygame.draw.line(surface, CYAN, aim + Vector2(0, offset * 5), aim + Vector2(0, offset * 13))
        if game.state != "playing":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((3, 8, 20, 190))
            surface.blit(overlay, (0, 0))
            if game.state == "paused":
                self.text(surface, "战斗暂停 · Esc 继续", (520, 280))
            else:
                self.text(surface, "任务完成" if game.state == "victory" else "任务失败", (570, 255))
                self.text(surface, f"Score {game.score}  /  Kills {game.kills}  /  Time {game.time:.1f}s", (440, 330))
            self.draw_buttons(surface, game)

    def draw_buttons(self, surface, game):
        for action, label, rect in game.buttons():
            active = action == game.selected_difficulty or rect.collidepoint(game.hover)
            pygame.draw.rect(surface, (24, 63, 80) if active else (17, 33, 52), rect, border_radius=8)
            pygame.draw.rect(surface, CYAN if active else (63, 94, 113), rect, 2, border_radius=8)
            text = self.font.render(label, True, CYAN if active else (205, 222, 237))
            surface.blit(text, text.get_rect(center=rect.center))

