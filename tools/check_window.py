"""真实 SDL 窗口中的可重复输入检查；不代替人工手感验收。"""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from pygame import Vector2
from game import Game
from render import Renderer
from settings import HEIGHT, WIDTH


def main():
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Alien Invasion — window check")
        game, renderer = Game(), Renderer()
        pygame.event.clear()
        start = game.player.pos.copy()
        game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d),
                            pygame.event.Event(pygame.MOUSEMOTION, pos=(120, 400))])
        game.update(.5)
        assert abs(game.player.pos.x - start.x - 170) < 1e-6
        assert game.player.pos.y == start.y
        assert game.player.direction.x < 0
        game.player.pos = start.copy()
        game.input.keys.add(pygame.K_w)
        game.update(.5)
        assert abs(game.player.pos.distance_to(start) - 170) < 1e-6
        game.input.keys.update((pygame.K_a, pygame.K_s))
        game.update(.5)
        assert abs(game.player.pos.distance_to(start) - 170) < 1e-6
        game.player.pos = Vector2(-100, 900)
        game.update(0)
        assert game.player.pos == Vector2(14, 706)
        game.player.pos = start.copy()
        game.input.clear()
        game.input.aim = start.copy()
        old_direction = game.player.direction.copy()
        game.update(0)
        assert game.player.direction == old_direction
        game.input.aim.update(640, 180)
        renderer.draw(surface, game)
        pygame.display.flip()
        output = ROOT / "docs/evidence/p1-window.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, output)
        for _ in range(90):
            pygame.event.pump()
            game.update(1 / 60)
            renderer.draw(surface, game)
            pygame.display.flip()
            pygame.time.wait(16)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        game.handle_events(pygame.event.get())
        assert not game.running
        print("PASS: real window, render, movement, aim, bounds, QUIT; Python", sys.version.split()[0], "pygame", pygame.version.ver)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
