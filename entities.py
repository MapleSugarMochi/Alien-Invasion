"""对象保存局部状态，不依赖游戏控制器或显示层。"""
from dataclasses import dataclass, field
import math

from pygame import Vector2

from settings import ENEMY_STATS, HEIGHT, HUD_HEIGHT, PLAYER_HP, PLAYER_RADIUS, PLAYER_SPEED, WIDTH


@dataclass
class Player:
    pos: Vector2 = field(default_factory=lambda: Vector2(640, 392))
    direction: Vector2 = field(default_factory=lambda: Vector2(0, -1))
    hp: int = PLAYER_HP
    radius: int = PLAYER_RADIUS
    invulnerable_until: float = 0.0
    previous: Vector2 = field(default_factory=lambda: Vector2(640, 392))

    def update(self, dt: float, movement: Vector2, aim: Vector2) -> None:
        self.previous = self.pos.copy()
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
    kind: str = "scout"
    settled: bool = False
    previous: Vector2 = field(init=False)
    speed: float = 180
    route: str = "straight"
    born_at: float = 0
    age: float = 0
    entered: bool = False
    mode: str = "entering"
    hold_until: float = 0
    next_shot: float = float("inf")
    fire_interval: float = float("inf")
    bullet_speed: float = 0
    bullet_damage: int = 0
    horizontal: int = 1
    origin_x: float = field(init=False)
    side_entry: int = 0

    def __post_init__(self) -> None:
        self.previous = self.pos.copy()
        self.origin_x = self.pos.x

    @property
    def damageable(self) -> bool:
        return self.hp > 0

    @property
    def on_screen(self):
        return 0 <= self.pos.x <= WIDTH and HUD_HEIGHT <= self.pos.y <= HEIGHT

    @property
    def gone(self):
        return self.entered and not (-self.radius <= self.pos.x <= WIDTH + self.radius
                                    and self.pos.y <= HEIGHT + self.radius)

    def update(self, dt, now, player_pos):
        self.previous = self.pos.copy()
        self.age += dt
        shots = []
        if self.side_entry and self.mode == "entering" and self.kind != "scout":
            destination = Vector2(240 if self.side_entry == 1 else 1040,
                                  180 if self.kind == "shooter" else 150)
            delta = destination - self.pos
            if delta.length() <= self.speed * dt:
                self.pos = destination
                self.begin_hold(now)
            else:
                self.pos += delta.normalize() * self.speed * dt
        elif self.kind == "scout":
            if self.side_entry:
                self.pos += Vector2(self.side_entry, 1).normalize() * self.speed * dt
            elif self.route in ("diagonal_left", "diagonal_right"):
                angle = -25 if self.route == "diagonal_left" else 25
                self.pos += Vector2(0, 1).rotate(angle) * self.speed * dt
            else:
                self.pos.y += self.speed * dt
                if self.route == "sway":
                    self.pos.x = self.origin_x + 70 * math.sin(self.age * math.pi)
        elif self.mode == "entering":
            stop = 180 if self.kind == "shooter" else 150
            self.pos.y = min(stop, self.pos.y + self.speed * dt)
            if self.pos.y >= stop:
                self.begin_hold(now)
        elif self.mode == "holding" and now < self.hold_until:
            if self.kind == "shooter":
                self.pos.x += self.horizontal * self.speed * dt
                if self.pos.x >= 1160 or self.pos.x <= 120:
                    self.pos.x = max(120, min(1160, self.pos.x))
                    self.horizontal *= -1
            else:
                self.pos.x = self.origin_x + 60 * math.sin((now - self.hold_until + 10) * math.pi / 2)
        else:
            self.mode = "leaving"
            self.pos.y += self.speed * dt
        if self.on_screen:
            self.entered = True
        if self.kind != "scout" and self.on_screen and now >= self.born_at + .5 and now + 1e-9 >= self.next_shot:
            direction = player_pos - self.pos
            if direction.length_squared():
                direction = direction.normalize()
                shots = [direction.rotate(angle) for angle in ((-20, 0, 20) if self.kind == "heavy" else (0,))]
                self.next_shot = now + self.fire_interval
        return shots

    def begin_hold(self, now):
        self.mode = "holding"
        self.hold_until = now + (8 if self.kind == "shooter" else 10)
        self.origin_x = self.pos.x

    @classmethod
    def create(cls, entity_id, kind, pos, difficulty, now, route="straight", side=0):
        hp, radius, speed, interval, bullet_speed, damage, _ = ENEMY_STATS[kind]
        enemy = cls(entity_id, Vector2(pos), radius, difficulty.hp(hp), kind)
        enemy.speed = speed * difficulty.movement
        enemy.fire_interval = interval * difficulty.fire_interval if interval else float("inf")
        enemy.bullet_speed = bullet_speed * difficulty.bullet_speed
        enemy.bullet_damage = difficulty.hit(damage) if damage else 0
        enemy.born_at, enemy.next_shot = now, now + .5
        enemy.route, enemy.side_entry = route, side
        return enemy


@dataclass
class Meteor:
    id: int
    pos: Vector2
    radius: int = 22
    hp: int = 40
    velocity: Vector2 = field(default_factory=lambda: Vector2(0, 120))
    previous: Vector2 = field(init=False)
    angle: float = 0.0

    def __post_init__(self) -> None:
        self.previous = self.pos.copy()

    @property
    def damageable(self) -> bool:
        return self.hp > 0

    def update(self, dt: float) -> None:
        self.previous = self.pos.copy()
        self.pos += self.velocity * dt
        self.angle += 25 * dt


@dataclass
class Pickup:
    id: int
    pos: Vector2
    born_at: float
    kind: str = "health"
    radius: int = 14
    consumed: bool = False

    def update(self, dt):
        self.pos.y += 45 * dt

    def expired(self, now):
        return self.consumed or now + 1e-9 >= self.born_at + 10 or self.pos.y - self.radius > HEIGHT

