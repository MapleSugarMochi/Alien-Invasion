"""统一的美术语言；简单图标与效果使用可编辑的原生绘图。"""
import math

import pygame

from settings import BACKGROUND, CYAN


INK = BACKGROUND
ICE = CYAN
PAPER = (221, 228, 230)
MUTED = (145, 161, 172)
SLATE = (41, 54, 66)
PANEL = (17, 25, 34)
PANEL_ACTIVE = (28, 43, 52)
LINE = (58, 75, 87)
CORAL = (209, 132, 119)
HEALTH = (147, 200, 183)
MISSILE = (212, 188, 145)
ARC = (171, 183, 212)


def corner_frame(surface, color, rect, length=8, width=1):
    """角标保持目标中部可见，也可用于选中卡片。"""
    rect = pygame.Rect(rect)
    length = min(length, rect.width // 2, rect.height // 2)
    for x, dx in ((rect.left, 1), (rect.right - 1, -1)):
        for y, dy in ((rect.top, 1), (rect.bottom - 1, -1)):
            pygame.draw.lines(surface, color, False,
                              [(x + dx * length, y), (x, y), (x, y + dy * length)], width)


def icon(name, size=48):
    """固定比例描绘，与字号或生成图集的裁切位置无关。"""
    scale = 3
    side = size * scale
    image = pygame.Surface((side, side), pygame.SRCALPHA)
    unit = side / 48

    def point(x, y):
        return round(x * unit), round(y * unit)

    def line(points, color=PAPER, width=2, closed=False):
        pygame.draw.lines(image, color, closed, [point(x, y) for x, y in points],
                          max(1, round(width * unit)))

    def polygon(points, color=PAPER):
        pygame.draw.polygon(image, color, [point(x, y) for x, y in points])

    if name == "health":
        rect = pygame.Rect(*point(10, 4), *point(28, 40))
        pygame.draw.rect(image, PAPER, rect, max(1, round(unit * 1.4)), border_radius=round(unit * 9))
        line([(24, 15), (24, 33)], HEALTH, 3)
        line([(15, 24), (33, 24)], HEALTH, 3)
    elif name == "missile":
        line([(24, 3), (44, 24), (24, 45), (4, 24)], closed=True, width=1.4)
        polygon([(24, 11), (28, 18), (28, 31), (20, 31), (20, 18)], PAPER)
        polygon([(20, 26), (16, 32), (16, 35), (22, 31)])
        polygon([(28, 26), (32, 32), (32, 35), (26, 31)])
        line([(24, 33), (24, 38)], MISSILE, 2)
    elif name == "arc":
        line([(14, 5), (34, 5), (44, 16), (44, 32), (34, 43), (14, 43), (4, 32), (4, 16)],
             ICE, 1.4, True)
        polygon([(27, 10), (16, 27), (23, 27), (20, 38), (33, 21), (26, 21)], PAPER)
    elif name == "support":
        center = point(24, 24)
        pygame.draw.circle(image, PAPER, center, round(18 * unit), max(1, round(unit * 1.4)))
        pygame.draw.circle(image, ICE, center, round(5 * unit))
        for angle in (0, 120, 240):
            x, y = 24 + math.cos(math.radians(angle)) * 17, 24 + math.sin(math.radians(angle)) * 17
            pygame.draw.circle(image, ICE, point(x, y), round(2.5 * unit))
    elif name == "crosshair":
        for a, b in (((5, 24), (17, 24)), ((31, 24), (43, 24)),
                     ((24, 5), (24, 17)), ((24, 31), (24, 43))):
            line([a, b], PAPER, 1)
    elif name == "lock":
        corner_frame(image, PAPER, (round(5 * unit), round(5 * unit), round(38 * unit), round(38 * unit)),
                     round(9 * unit), max(1, round(unit)))
    elif name == "pulse":
        line([(24, 7), (24, 41)], ICE, 3)
        line([(24, 12), (24, 36)], PAPER, 1)
    elif name == "explosion":
        center = point(24, 24)
        for angle in range(0, 360, 45):
            direction = pygame.Vector2(0, -1).rotate(angle)
            start = pygame.Vector2(center) + direction * 10 * unit
            end = pygame.Vector2(center) + direction * (17 + angle % 3) * unit
            pygame.draw.line(image, CORAL, start, end, max(1, round(unit)))
        pygame.draw.circle(image, PAPER, center, round(4 * unit))
    else:
        raise KeyError(f"未知绘图图标：{name}")
    return pygame.transform.smoothscale(image, (size, size))
