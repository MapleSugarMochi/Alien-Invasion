"""P1 几何占位画面；资源由显示层统一管理。"""
import math
import random

import pygame
from pygame import Vector2

from settings import BACKGROUND, CYAN, HEIGHT, HUD_HEIGHT, WIDTH


class Renderer:
    def __init__(self) -> None:
        self.font = pygame.font.Font(None, 26)
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
        for enemy in game.enemies:
            self.ship(surface, enemy.pos, Vector2(0, 1), enemy.radius, (240, 124, 110))
        for meteor in game.meteors:
            pygame.draw.circle(surface, (142, 152, 176), meteor.pos, meteor.radius, 2)
        for projectile in game.projectiles + game.enemy_bullets:
            color = (255, 112, 88) if projectile.source == "enemy" else CYAN
            pygame.draw.circle(surface, color, projectile.pos, projectile.radius)
        for until, pos, radius in game.effects:
            pygame.draw.circle(surface, (255, 205, 132), pos, radius, 1)
        if game.time >= game.player.invulnerable_until or int(game.time * 18) % 2:
            self.ship(surface, game.player.pos, game.player.direction, 23, CYAN)
        pygame.draw.rect(surface, (13, 24, 42), (0, 0, WIDTH, HUD_HEIGHT))
        self.text(surface, f"HP {game.player.hp:3}   /   SCORE {game.score}   /   KILLS {game.kills}", (24, 21))
        self.text(surface, "WASD move   /   Mouse aim & fire   /   Esc pause", (650, 21))
        aim = Vector2(max(0, min(WIDTH, game.input.aim.x)),
                      max(HUD_HEIGHT, min(HEIGHT, game.input.aim.y)))
        for offset in (-1, 1):
            pygame.draw.line(surface, CYAN, aim + Vector2(offset * 5, 0), aim + Vector2(offset * 13, 0))
            pygame.draw.line(surface, CYAN, aim + Vector2(0, offset * 5), aim + Vector2(0, offset * 13))
        if game.state != "playing":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((3, 8, 20, 190))
            surface.blit(overlay, (0, 0))
            self.text(surface, "PAUSED — Esc to resume" if game.state == "paused" else "DEFEAT", (500, 340))

