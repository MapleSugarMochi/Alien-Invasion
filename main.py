"""窗口与主循环入口；导入本模块不会创建窗口。"""
import argparse
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from game import Game
from render import Renderer
from preferences import Preferences
from settings import FPS, HEIGHT, WIDTH


def run() -> None:
    parser = argparse.ArgumentParser(description="Alien Invasion")
    parser.parse_args()
    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        clock = pygame.time.Clock()
        game, renderer = Game(menu=True, preferences=Preferences.load()), Renderer()
        display_language = game.language
        pygame.display.set_caption(game.text("window_title"))
        while game.running:
            dt = clock.tick(FPS) / 1000.0
            game.handle_events(pygame.event.get())
            if game.language != display_language:
                pygame.display.set_caption(game.text("window_title"))
                display_language = game.language
            game.update(dt)
            renderer.feedback(game)
            renderer.draw(screen, game)
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    run()
