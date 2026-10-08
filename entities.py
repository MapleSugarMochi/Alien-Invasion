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
    training: bool = False
    training_sway: bool = False

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
        if self.training:
            # 靶机仍使用真实伤害和碰撞，仅停止攻击／离场；导弹靶轻微横移。
            if self.training_sway:
                self.pos.x = self.origin_x + 40 * math.sin(self.age)
            return []
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
        if self.kind != "scout" and self.on_screen and now + 1e-9 >= self.born_at + .5 and now + 1e-9 >= self.next_shot:
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


@dataclass
class Boss:
    id: int
    difficulty: object
    pos: Vector2 = field(default_factory=lambda: Vector2(640, 4))
    radius: int = 60
    kind: str = "boss"
    hp: int = field(init=False)
    max_hp: int = field(init=False)
    previous: Vector2 = field(init=False)
    entering: bool = True
    settled: bool = False
    phase: int = 1
    transition_until: float = 0
    horizontal: int = 1
    next_round: float = float("inf")
    burst: list = field(default_factory=list)
    next_fan: bool = True
    base_hp: int = 2400

    def __post_init__(self):
        self.max_hp = self.hp = self.difficulty.hp(self.base_hp)
        self.previous = self.pos.copy()

    @property
    def damageable(self):
        return self.hp > 0 and not self.entering

    @property
    def on_screen(self):
        return 0 <= self.pos.x <= WIDTH and HUD_HEIGHT <= self.pos.y <= HEIGHT

    def health_phase(self):
        return 1 if self.hp * 3 > self.max_hp * 2 else (3 if self.hp * 3 < self.max_hp else 2)

    def interval(self):
        return {1: 1.4, 2: 1.1, 3: .9}[self.phase] * self.difficulty.fire_interval

    def reset_schedule(self, now):
        self.next_round = now + self.interval()
        self.burst.clear()
        self.next_fan = True

    def sync_phase(self, now):
        """立即撤销旧 AI；过渡中的后续伤害不能延长截止时间。"""
        if self.damageable and not self.transition_until and self.health_phase() != self.phase:
            self.transition_until = now + 1
            self.burst.clear()
            self.next_round = float("inf")
            return True
        return False

    def warning(self, now):
        return self.damageable and not self.transition_until and now + 1e-9 >= self.next_round - .6

    def update(self, dt, now, player_pos):
        self.previous = self.pos.copy()
        if self.hp <= 0:
            return []
        if self.entering:
            self.pos.y = min(180, self.pos.y + 100 * self.difficulty.movement * dt)
            if self.pos.y >= 180:
                self.entering = False
                self.reset_schedule(now)
            return []
        if self.transition_until:
            if now + 1e-9 >= self.transition_until:
                self.phase = self.health_phase()
                self.transition_until = 0
                self.reset_schedule(now)
            return []
        self.pos.x += self.horizontal * 120 * self.difficulty.movement * dt
        if self.pos.x <= 320 or self.pos.x >= 960:
            self.pos.x = max(320, min(960, self.pos.x))
            self.horizontal *= -1
        directions = []
        if now + 1e-9 >= self.next_round:
            if self.phase == 1 or (self.phase == 3 and self.next_fan):
                angles = (-30, -15, 0, 15, 30) if self.phase == 1 else (-45, -30, -15, 0, 15, 30, 45)
                directions.extend(Vector2(0, 1).rotate(a) for a in angles)
            else:
                self.burst.extend((now, now + .05, now + .1))
            if self.phase == 3:
                self.next_fan = not self.next_fan
            self.next_round = now + self.interval()
        while self.burst and self.burst[0] <= now + 1e-9:
            self.burst.pop(0)
            direction = player_pos - self.pos
            directions.append(direction.normalize() if direction.length_squared() else Vector2(0, 1))
        return directions

