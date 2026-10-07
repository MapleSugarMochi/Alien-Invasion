"""输入与游戏规则协调；显示层只读取这些状态。"""
from dataclasses import dataclass, field

import pygame
from pygame import Vector2

from entities import Enemy, Player
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

    def handle_events(self, events) -> None:
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.input.keys.add(event.key)
            elif event.type == pygame.KEYUP:
                self.input.keys.discard(event.key)
            elif event.type == pygame.MOUSEMOTION:
                self.input.aim.update(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.input.fire = True
                self.input.aim.update(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.input.fire = False

    def update(self, dt: float) -> None:
        if self.running and self.state == "playing":
            self.time += dt
            self.player.update(dt, self.input.movement, self.input.aim)

