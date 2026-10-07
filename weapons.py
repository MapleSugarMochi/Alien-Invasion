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


@dataclass
class SupportRound:
    number: int
    start: float
    ids: list
    launched: bool = False
    hit: bool = False


class SupportController:
    """有限五轮任务，稳定 ID 防止失效引用与同轮重复打击。"""
    def __init__(self):
        self.active = False
        self.start_at = 0.0
        self.end_at = 0.0
        self.round_count = 0
        self.rounds = []
        self.failed_until = 0.0

    def start(self, now):
        if self.active:
            return False
        self.active = True
        self.start_at, self.end_at = now, now + 7.5
        self.round_count = 0
        self.rounds.clear()
        return True

    def cancel(self):
        self.active = False
        self.rounds.clear()

    def expire(self, now):
        if self.active and now + 1e-9 >= self.end_at:
            self.cancel()
            return True
        return False

    def deadlines(self):
        if not self.active:
            return []
        times = [self.end_at]
        if self.round_count < 5:
            times.append(self.start_at + 1.5 * self.round_count)
        for round_ in self.rounds:
            if not round_.launched:
                times.append(round_.start + .4)
            if not round_.hit:
                times.append(round_.start + .65)
        return times

    def update(self, now, candidates, aim):
        if not self.active:
            return []
        events = []
        while self.round_count < 5 and now + 1e-9 >= self.start_at + self.round_count * 1.5:
            ids = [t.id for t in nearest_aim(candidates, aim)[:3]]
            round_ = SupportRound(self.round_count + 1, self.start_at + self.round_count * 1.5, ids)
            self.rounds.append(round_)
            self.round_count += 1
            events.append(("round", round_.number, list(ids)))
        available = nearest_aim(candidates, aim)
        valid_ids = {t.id for t in available}
        for round_ in self.rounds:
            if not round_.launched and now + 1e-9 >= round_.start + .4:
                assigned = set(round_.ids) & valid_ids
                replacement = []
                for target_id in round_.ids:
                    if target_id in valid_ids:
                        replacement.append(target_id)
                    else:
                        new = next((t.id for t in available if t.id not in assigned), None)
                        if new is not None:
                            assigned.add(new)
                            replacement.append(new)
                round_.ids = replacement
                round_.launched = True
                events.append(("launch", round_.number, list(replacement)))
            if not round_.hit and now + 1e-9 >= round_.start + .65:
                round_.hit = True
                events.append(("hit", round_.number, [i for i in round_.ids if i in valid_ids]))
        return events
