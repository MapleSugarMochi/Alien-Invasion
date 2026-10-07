"""共用圆形几何；旋转精灵不改变碰撞范围。"""
import math
from pygame import Vector2
from settings import WIDTH, HEIGHT


def circle_hit(start: Vector2, end: Vector2, center: Vector2, radius: float):
    """返回线段最早交圆的比例，初始重叠为 0，无交点为 None。"""
    offset, delta = start - center, end - start
    c = offset.length_squared() - radius * radius
    if c <= 0:
        return 0.0
    a = delta.length_squared()
    if a <= 1e-18:
        return None
    b = 2 * offset.dot(delta)
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None
    t = (-b - math.sqrt(discriminant)) / (2 * a)
    return t if 0 <= t <= 1 else None


def moving_hit(start, end, old_target, target, radius):
    return circle_hit(start - old_target, end - target, Vector2(), radius)


def screen_fraction(start, end):
    """截取弹丸中心出屏前的轨迹，避免回收后命中。"""
    if not (0 <= start.x <= WIDTH and 0 <= start.y <= HEIGHT):
        return 0.0
    fraction = 1.0
    for initial, final, maximum in ((start.x, end.x, WIDTH), (start.y, end.y, HEIGHT)):
        delta = final - initial
        if final < 0:
            fraction = min(fraction, -initial / delta)
        elif final > maximum:
            fraction = min(fraction, (maximum - initial) / delta)
    return fraction
