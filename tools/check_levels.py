"""真实 SDL 窗口验证三关卡入口、双语排版、输入、重开与返回。"""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from game import Game
from render import Renderer
from settings import HEIGHT, LEVELS, WIDTH


def main():
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        assert pygame.display.get_driver() == "windows", "需要 Windows 真实 SDL 窗口"
        pygame.display.set_caption("Alien Invasion - levels check")
        renderer = Renderer()
        output = ROOT / "docs/evidence/levels"
        output.mkdir(parents=True, exist_ok=True)
        original_text = renderer.text
        original_controls = renderer.draw_controls

        def checked_text(surface, message, pos, color=(205, 222, 237), anchor="topleft"):
            rect = renderer.font.render(message, True, color).get_rect(**{anchor: pos})
            assert surface.get_rect().contains(rect), f"文字溢出：{message}"
            original_text(surface, message, pos, color, anchor)

        def settings_controls(surface, game):
            assert game.state == "settings", "关卡页不应显示键位表"
            original_controls(surface, game)

        renderer.text = checked_text
        renderer.draw_controls = settings_controls

        def events(game, *items):
            pygame.event.clear()
            for event in items:
                pygame.event.post(event)
            game.handle_events(pygame.event.get())

        def button(game, action):
            rect = next(rect for name, _, rect in game.buttons() if name == action)
            events(game, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center),
                   pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center))

        def capture(game, name):
            renderer.draw(surface, game)
            pygame.display.flip()
            pygame.event.pump()
            pygame.image.save(surface, output / f"{name}.png")

        for language in ("en", "zh-CN"):
            game = Game(menu=True, language=language)
            button(game, "level_select")
            assert game.state == "level_select"
            entries = [rect for action, _, rect in game.buttons() if action.startswith("level_")]
            assert len(entries) == 3 and all(surface.get_rect().contains(rect) for rect in entries)
            assert not any(first.colliderect(second) for i, first in enumerate(entries) for second in entries[i + 1:])
            capture(game, f"{language}-levels")
            for level in LEVELS:
                button(game, "hard")
                button(game, f"level_{level}")
                assert (game.state, game.level, game.difficulty.id) == ("playing", level, "hard")
                assert not game.input.fire
                start = game.player.pos.copy()
                events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d),
                       pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 180)))
                game.update(.1)
                assert game.player.pos.x > start.x and game.projectiles
                capture(game, f"{language}-level-{level}")
                events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
                assert game.state == "paused"
                button(game, "settings")
                frozen = game.time
                game.update(1)
                assert game.time == frozen
                button(game, "settings_back")
                assert game.state == "paused"
                button(game, "restart")
                assert (game.state, game.level, game.time) == ("level_select", level, 0)
            events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            assert game.state == "main_menu"
            events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
            assert (game.state, game.level) == ("playing", 2)
            game.finish("defeat")
            events(game, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
            assert game.state == "level_select"
            button(game, "menu")
            assert game.state == "main_menu"
            events(game, pygame.event.Event(pygame.QUIT))
            assert not game.running
        result = {"status": "PASS", "driver": pygame.display.get_driver(),
                  "languages": ["en", "zh-CN"], "levels": list(LEVELS), "screenshots": 8,
                  "checks": "three cards, no controls table, text bounds, mouse entry, chosen difficulty, movement, shooting, pause/settings frozen, restart, keyboard entry, result retry, main menu, quit"}
        (output / "check.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
