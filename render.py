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
        self.ship(surface, game.player.pos, game.player.direction, 23, CYAN)
        pygame.draw.rect(surface, (13, 24, 42), (0, 0, WIDTH, HUD_HEIGHT))
        self.text(surface, "ALIEN INVASION  /  P1 INPUT PROTOTYPE", (24, 21))
        self.text(surface, "WASD move   /   Mouse aim   /   Close window to exit", (660, 21))
        aim = Vector2(max(0, min(WIDTH, game.input.aim.x)),
                      max(HUD_HEIGHT, min(HEIGHT, game.input.aim.y)))
        for offset in (-1, 1):
            pygame.draw.line(surface, CYAN, aim + Vector2(offset * 5, 0), aim + Vector2(offset * 13, 0))
            pygame.draw.line(surface, CYAN, aim + Vector2(0, offset * 5), aim + Vector2(0, offset * 13))

