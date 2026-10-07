"""P1 几何占位画面；资源由显示层统一管理。"""
import math
import random

import pygame
from pygame import Vector2

from settings import BACKGROUND, CYAN, HEIGHT, HUD_HEIGHT, WIDTH


class Renderer:
    def __init__(self) -> None:
        self.font_path = pygame.font.match_font(["microsoftyahei", "simhei", "simsun"])
        self.font = pygame.font.Font(self.font_path, 20)
        self.large_font = pygame.font.Font(self.font_path, 42)
        rng = random.Random(1)
        self.stars = [(rng.randrange(WIDTH), rng.randrange(HEIGHT), rng.uniform(15, 65))
                      for _ in range(160)]

    def text(self, surface, message, pos, color=(205, 222, 237)) -> None:
        surface.blit(self.font.render(message, True, color), pos)

    def ship(self, surface, pos, direction, size, color) -> None:
        side = Vector2(-direction.y, direction.x)
        points = [pos + direction * size, pos - direction * size * .7 + side * size * .8,
                  pos - direction * size * .35, pos - direction * size * .7 - side * size * .8]
        pygame.draw.polygon(surface, color, points, 2)

    def draw(self, surface, game) -> None:
        surface.fill(BACKGROUND)
        for x, y, speed in self.stars:
            pygame.draw.circle(surface, (90, 120, 153), (x, int((y + game.time * speed) % HEIGHT)), 1)
        if game.state in ("main_menu", "setup"):
            title = "ALIEN INVASION" if game.state == "main_menu" else "出击准备"
            heading = self.large_font.render(title, True, CYAN)
            surface.blit(heading, heading.get_rect(center=(640, 155)))
            if game.state == "main_menu":
                self.ship(surface, Vector2(640, 280), Vector2(0, -1), 52, CYAN)
                self.text(surface, "生存 · 12 波敌群 · 外星母舰", (475, 205))
            else:
                instructions = ["WASD 按屏幕方向移动，鼠标瞄准，按住左键持续射击",
                                "Esc 暂停／继续；窗口失焦自动暂停，继续后重新按左键",
                                "拾取绿色回血补给 +25 生命，每 7 秒生成，满血不消耗",
                                "完成 12 波并击毁母舰获胜；生命归零失败；重开清空本局",
                                "选择难度（也可按 1 / 2 / 3），Enter 开始"]
                for index, line in enumerate(instructions):
                    self.text(surface, line, (305, 250 + index * 36))
            self.draw_buttons(surface, game)
            return
        for enemy in game.enemies:
            colors = {"scout": (240, 124, 110), "shooter": (255, 184, 77), "heavy": (186, 130, 244)}
            self.ship(surface, enemy.pos, Vector2(0, 1), enemy.radius, colors[enemy.kind])
        if game.boss and game.boss.hp > 0:
            boss = game.boss
            pygame.draw.ellipse(surface, (186, 130, 244), (*tuple(boss.pos - Vector2(95, 45)), 190, 90), 3)
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
            pygame.draw.circle(surface, (142, 152, 176), meteor.pos, meteor.radius, 2)
        for projectile in game.projectiles + game.enemy_bullets:
            color = (255, 112, 88) if projectile.source == "enemy" else CYAN
            pygame.draw.circle(surface, color, projectile.pos, projectile.radius)
        for until, pos, radius in game.effects:
            pygame.draw.circle(surface, (255, 205, 132), pos, radius, 1)
        for pickup in game.pickups:
            pygame.draw.rect(surface, (117, 237, 158), (*tuple(pickup.pos - Vector2(13, 13)), 26, 26), 2)
            self.text(surface, "+", pickup.pos - Vector2(7, 10), (117, 237, 158))
        if game.meteor_warning:
            _, x, _ = game.meteor_warning
            pygame.draw.polygon(surface, (255, 184, 77), [(x - 12, 72), (x + 12, 72), (x, 91)], 2)
        if game.time >= game.player.invulnerable_until or int(game.time * 18) % 2:
            self.ship(surface, game.player.pos, game.player.direction, 23, CYAN)
        pygame.draw.rect(surface, (13, 24, 42), (0, 0, WIDTH, HUD_HEIGHT))
        self.text(surface, f"HP {game.player.hp:3}   /   SCORE {game.score}   /   KILLS {game.kills}", (24, 21))
        self.text(surface, "WASD move   /   Mouse aim & fire   /   Esc pause", (650, 21))
        self.text(surface, f"WAVE {game.wave.number}/12   {game.phase.upper()}", (24, 83))
        self.text(surface, game.difficulty.label, (1190, 82))
        aim = Vector2(max(0, min(WIDTH, game.input.aim.x)),
                      max(HUD_HEIGHT, min(HEIGHT, game.input.aim.y)))
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

