"""集中配置；坐标和速度均使用逻辑画面与秒。"""
from pathlib import Path
from dataclasses import dataclass, replace
import math

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT, HUD_HEIGHT = 1280, 720, 64
FPS = 60
LEVELS = (1, 2, 3)
PLAYER_SPEED, PLAYER_RADIUS, PLAYER_HP = 340.0, 14, 100
BACKGROUND = (5, 10, 23)
CYAN = (84, 225, 245)


@dataclass(frozen=True)
class Difficulty:
    id: str
    label: str
    health: float
    movement: float
    bullet_speed: float
    fire_interval: float
    damage: float
    enemy_cap: int
    meteor_interval: float
    meteor_cap: int

    def hp(self, base):
        return max(1, math.floor(base * self.health))

    def hit(self, base):
        return max(1, math.floor(base * self.damage))


DIFFICULTIES = {
    "easy": Difficulty("easy", "简单", .8, .8, .75, 1.3, .75, 3, 16 / 3, 2),
    "standard": Difficulty("standard", "标准", 1, 1, 1, 1, 1, 5, 4, 3),
    "hard": Difficulty("hard", "困难", 1.25, 1.2, 1.25, .8, 1.2, 8, 8 / 3, 4),
}
ENEMY_STATS = {
    "scout": (20, 16, 180, 0, 0, 0, 100),
    "shooter": (50, 22, 110, 1.5, 250, 10, 200),
    "heavy": (120, 30, 70, 2, 200, 15, 500),
}
# (侦察、射手、重型、生成间隔)；入口和路线由 wave_spawn 统一解释。
WAVES = (
    (8, 0, 0, .9), (7, 1, 0, .9), (6, 2, 0, .85), (6, 2, 1, .85),
    (5, 3, 1, .8), (5, 3, 2, .8), (4, 4, 2, .75), (4, 4, 2, .75),
    (5, 4, 2, .7), (4, 4, 3, .65), (4, 5, 3, .6), (4, 4, 4, .6),
)


@dataclass(frozen=True)
class LevelConfig:
    waves: tuple
    boss_base_hp: int = 2400


# 教程使用标准对象数值，通过投放密度降低压力，不改变已选正式难度。
TUTORIAL_DIFFICULTY = replace(DIFFICULTIES["standard"], enemy_cap=2, meteor_interval=8, meteor_cap=1)
TUTORIAL_WAVES = ((6, 0, 0, 1.2), (3, 2, 1, 1.4))
TUTORIAL_TRANSITION = .8
TUTORIAL_PLAYER_POS = (640, 560)
TUTORIAL_ARC_POS = (640, 500)
TUTORIAL_ARC_TARGETS = ((550, 310), (640, 290), (730, 310))

# 关卡 1 由 TutorialController 调度；关卡 2 为原战斗基线。
# 关卡 3 合计 round(118 * 1.2) = 142 架；按原机型比例取整为 75/43/24。
# 增量分散到原有 12 波，生成间隔、路线及难度的场内上限保持原值。
LEVEL_CONFIGS = {
    1: LevelConfig(TUTORIAL_WAVES),
    2: LevelConfig(WAVES),
    3: LevelConfig((
        (10, 0, 0, .9), (8, 1, 0, .9), (7, 2, 0, .85), (7, 2, 1, .85),
        (6, 3, 1, .8), (6, 4, 2, .8), (5, 5, 2, .75), (5, 5, 2, .75),
        (6, 5, 3, .7), (5, 5, 4, .65), (5, 6, 4, .6), (5, 5, 5, .6),
    ), boss_base_hp=3360),
}

