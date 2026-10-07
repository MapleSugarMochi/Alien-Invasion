"""集中配置；坐标和速度均使用逻辑画面与秒。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT, HUD_HEIGHT = 1280, 720, 64
FPS = 60
PLAYER_SPEED, PLAYER_RADIUS, PLAYER_HP = 340.0, 14, 100
BACKGROUND = (5, 10, 23)
CYAN = (84, 225, 245)

