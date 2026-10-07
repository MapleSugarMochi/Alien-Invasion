"""攻击请求、弹丸与共用冷却，不修改全局生命或统计。"""
from dataclasses import dataclass
import math
from pygame import Vector2

from geometry import screen_fraction


def valid_targets(candidates):
    return [t for t in candidates if t.damageable and t.on_screen]


def nearest_aim(candidates, aim):
    return sorted(valid_targets(candidates), key=lambda t: (t.pos.distance_squared_to(aim), t.id))


def arc_chain(player, aim, candidates):
    enemies = valid_targets(candidates)
    first = []
    for enemy in enemies:
        direction = enemy.pos - player.pos
        distance = direction.length()
        if distance <= 300 + 1e-9 and (distance == 0 or player.direction.dot(direction / distance) >= math.sqrt(.5) - 1e-9):
            first.append(enemy)
    ordered = nearest_aim(first, aim)
    if not ordered:
        return []
    chain = [ordered[0]]
    while len(chain) < 3:
        available = [e for e in enemies if e not in chain and e.pos.distance_to(chain[-1].pos) <= 130 + 1e-9]
        if not available:
            break
        chain.append(min(available, key=lambda e: (e.pos.distance_squared_to(chain[-1].pos), e.id)))
    return chain


@dataclass
class Projectile:
    pos: Vector2
    velocity: Vector2
    damage: int = 10
    radius: int = 3
    source: str = "bullet"
    remaining_range: float = 900.0
    remaining_life: float = float("inf")
    alive: bool = True

    def advance(self, dt):
        start = self.pos.copy()
        speed = self.velocity.length()
        available = min(dt, self.remaining_life, self.remaining_range / speed if speed else dt)
        end = start + self.velocity * available
        fraction = screen_fraction(start, end)
        end = start.lerp(end, fraction)
        travelled = start.distance_to(end)
        self.pos = end
        self.remaining_range = max(0.0, self.remaining_range - travelled)
        self.remaining_life -= dt
        expired = fraction < 1 or self.remaining_range <= 1e-7 or self.remaining_life <= 1e-7
        return start, end, (available / dt * fraction if dt else 0), expired


class Missile(Projectile):
    def __init__(self, pos, direction):
        super().__init__(pos, direction * 420, 60, 6, "missile", float("inf"), 3)
        self.target_id = None

    def turn(self, dt, candidates, aim):
        candidates = [t for t in valid_targets(candidates) if self.pos.distance_to(t.pos) <= 650 + 1e-9]
        target = next((t for t in candidates if t.id == self.target_id), None)
        if target is None:
            ordered = nearest_aim(candidates, aim)
            target = ordered[0] if ordered else None
            self.target_id = target.id if target else None
        if target:
            desired = target.pos - self.pos
            if desired.length_squared():
                angle = self.velocity.angle_to(desired)
                angle = (angle + 180) % 360 - 180
                self.velocity = self.velocity.rotate(max(-360 * dt, min(360 * dt, angle)))


@dataclass
class ArcAttack:
    targets: list


class WeaponController:
    intervals = {"bullet": .12, "missile": .4, "arc": .2}

    def __init__(self):
        self.last_shot_at = None
        self.ready_at = 0.0
        self.active = "bullet"
        self.active_until = 0.0
        self.charges = {"missile": 0, "arc": 0}
        self.failed_until = {"missile": 0.0, "arc": 0.0}

    @property
    def interval(self):
        return self.intervals[self.active]

    def switch(self, kind):
        self.active = kind
        if self.last_shot_at is not None:
            self.ready_at = max(self.ready_at, self.last_shot_at + self.interval)

    def expire(self, now):
        if self.active != "bullet" and now + 1e-9 >= self.active_until:
            self.switch("bullet")
            self.active_until = 0

    def try_activate(self, kind, now):
        self.expire(now)
        if self.active != "bullet" or self.charges[kind] < 3:
            self.failed_until[kind] = now + .3
            return False
        self.charges[kind] = 0
        self.active_until = now + 5
        self.switch(kind)
        return True

    def try_fire(self, now, player, aim=None, targets=()):
        if now + 1e-9 < self.ready_at:
            return None
        self.last_shot_at, self.ready_at = now, now + self.interval
        if self.active == "missile":
            return Missile(player.pos + player.direction * 24, player.direction)
        if self.active == "arc":
            return ArcAttack(arc_chain(player, aim if aim is not None else player.pos + player.direction * 300, targets))
        return Projectile(player.pos + player.direction * 24, player.direction * 900)
