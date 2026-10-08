"""普通波次队列：入场对象占名额，满额不累计补发。"""
from collections import deque

from entities import Enemy
from settings import WAVES


class WaveController:
    def __init__(self, number, now):
        self.number = number
        remaining = list(WAVES[number - 1][:3])
        self.interval = WAVES[number - 1][3]
        self.queue = deque()
        while any(remaining):
            for index, kind in enumerate(("scout", "shooter", "heavy")):
                if remaining[index]:
                    self.queue.append(kind)
                    remaining[index] -= 1
        self.next_spawn = now
        self.spawned = 0

    def update(self, now, active_count, difficulty, next_id):
        if not self.queue or now + 1e-9 < self.next_spawn or active_count >= difficulty.enemy_cap:
            return None
        kind = self.queue.popleft()
        index = self.spawned
        self.spawned += 1
        self.next_spawn = now + self.interval
        return wave_spawn(next_id, kind, self.number, index, difficulty, now)


def wave_spawn(entity_id, kind, wave, index, difficulty, now):
    lanes = (160, 352, 544, 736, 928, 1120)
    if wave == 1:
        lanes = (480, 800)
    elif wave in (2, 6):
        lanes = (240, 1040)
    elif wave in (4, 7):
        lanes = (320, 640, 960)
    elif wave == 8:
        lanes = tuple(reversed(lanes))
    x = lanes[index % len(lanes)]
    route, side = "straight", 0
    if wave in (3, 7, 11) or (wave in (9, 12) and index % 2):
        route = "sway"
    elif wave in (2, 5):
        route = "diagonal_left" if x < 640 else "diagonal_right"
    if wave == 4 and kind == "heavy":
        x = 640
    elif wave == 8 and kind == "heavy":
        x = (480, 800)[index // 3 % 2]
    elif wave == 12 and kind == "heavy":
        x = (160, 480, 800, 1120)[index // 3 % 4]
    if wave == 10:
        side = 1 if index % 2 == 0 else -1
    radius = {"scout": 16, "shooter": 22, "heavy": 30}[kind]
    pos = ((-radius if side == 1 else 1280 + radius), 110) if side else (x, 64 - radius)
    return Enemy.create(entity_id, kind, pos, difficulty, now, route, side)
