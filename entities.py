"""对象保存局部状态，不依赖游戏控制器或显示层。"""
from dataclasses import dataclass, field

from pygame import Vector2

from settings import HEIGHT, HUD_HEIGHT, PLAYER_HP, PLAYER_RADIUS, PLAYER_SPEED, WIDTH


@dataclass
class Player:
    pos: Vector2 = field(default_factory=lambda: Vector2(640, 392))
    direction: Vector2 = field(default_factory=lambda: Vector2(0, -1))
    hp: int = PLAYER_HP
    radius: int = PLAYER_RADIUS

    def update(self, dt: float, movement: Vector2, aim: Vector2) -> None:
        if movement.length_squared():
            self.pos += movement.normalize() * PLAYER_SPEED * dt
        self.clamp()
        facing = aim - self.pos
        if facing.length_squared():
            self.direction = facing.normalize()

    def clamp(self) -> None:
        self.pos.x = max(self.radius, min(WIDTH - self.radius, self.pos.x))
        self.pos.y = max(HUD_HEIGHT + self.radius, min(HEIGHT - self.radius, self.pos.y))


@dataclass
class Enemy:
    id: int
    pos: Vector2
    radius: int = 16
    hp: int = 20

