"""攻击请求、弹丸与共用冷却，不修改全局生命或统计。"""
from dataclasses import dataclass
from pygame import Vector2

from geometry import screen_fraction


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


class WeaponController:
    interval = .12

    def __init__(self):
        self.last_shot_at = None
        self.ready_at = 0.0

    def try_fire(self, now, player):
        if now + 1e-9 < self.ready_at:
            return None
        self.last_shot_at, self.ready_at = now, now + self.interval
        return Projectile(player.pos + player.direction * 24, player.direction * 900)
