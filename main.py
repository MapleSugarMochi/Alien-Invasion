"""窗口与主循环入口；导入本模块不会创建窗口。"""
import argparse
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from game import Game
from render import Renderer
from settings import FPS, HEIGHT, WIDTH


def run() -> None:
    parser = argparse.ArgumentParser(description="Alien Invasion")
    parser.parse_args()
    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Alien Invasion")
        clock = pygame.time.Clock()
        game, renderer = Game(), Renderer()
        while game.running:
            dt = clock.tick(FPS) / 1000.0
            game.handle_events(pygame.event.get())
            game.update(dt)
            renderer.draw(screen, game)
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
