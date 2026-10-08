"""真实 SDL 窗口检查双语显示、设置页语言选择；保存截图并检查文字边界。"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from entities import Boss
from game import Game
from localization import TEXT
from render import Renderer
from settings import HEIGHT, WIDTH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence/settings/language")
    args = parser.parse_args()
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        assert pygame.display.get_driver() != "dummy", "需要真实 SDL 窗口"
        pygame.display.set_caption("Alien Invasion - language check")
        renderer = Renderer()
        output = args.output
        output.mkdir(parents=True, exist_ok=True)
        bounds = surface.get_rect()
        draw_text = renderer.text
        checked_texts = []

        def checked_text(surface, message, pos, color=(205, 222, 237), anchor="topleft"):
            rect = renderer.font.render(message, True, color).get_rect(**{anchor: pos})
            assert bounds.contains(rect), f"文字超出窗口：{message} {rect}"
            checked_texts.append(message)
            draw_text(surface, message, pos, color, anchor)

        renderer.text = checked_text
        # Windows 系统中文字体需实际包含字形，不能以无异常代替字体显示验收。
        chinese = sorted({char for text in TEXT["zh-CN"].values() for char in text
                          if "\u4e00" <= char <= "\u9fff"})
        assert all(metric is not None for metric in renderer.font.metrics("".join(chinese))), "中文字体缺少字形"
        game = Game(menu=True)
        assert game.language == "en"
        for language in TEXT:
            if game.language != language:
                game.menu_action("settings")
                rect = next(rect for action, _, rect in game.buttons() if action == "language_" + language)
                game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)])
                game.menu_action("settings_back")
            assert game.language == language
            for state in ("main_menu", "level_select", "settings", "playing", "paused", "victory", "defeat"):
                game.state = state
                renderer.draw(surface, game)
                for _, label, rect in game.buttons():
                    text_rect = renderer.font.render(label, True, (255, 255, 255)).get_rect(center=rect.center)
                    assert rect.inflate(-16, -4).contains(text_rect), f"按钮文字溢出：{label}"
                pygame.display.flip()
                pygame.image.save(surface, output / f"{language}-{state}.png")
                pygame.event.pump()
                pygame.time.wait(80)
            game.state = "playing"
            for phase in ("rest", "meteor_clear", "boss_warning", "boss_entry", "boss_fight"):
                game.phase = phase
                renderer.draw(surface, game)
            game.boss = Boss(999, game.difficulty)
            game.boss.pos.update(640, 180)
            game.boss.transition_until = 1
            for weapon in ("bullet", "missile", "arc"):
                game.weapons.active = weapon
                game.weapons.active_until = 5
                renderer.draw(surface, game)
            game.support.active = True
            game.support.end_at = 7.5
            renderer.draw(surface, game)
            pygame.display.flip()
            pygame.image.save(surface, output / f"{language}-boss.png")
            game.to_menu()
            assert game.language == language
        game.menu_action("level_select")
        game.menu_action("level_1")
        game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1),
                            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d),
                            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 180))])
        assert game.language == "zh-CN"  # F1 不再切换语言。
        start = game.player.pos.copy()
        game.update(.1)
        assert game.player.pos.x > start.x and game.projectiles
        game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
                            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1)])
        assert (game.state, game.language) == ("paused", "zh-CN")
        frozen = game.time
        game.update(1)
        assert game.time == frozen
        game.menu_action("restart")
        assert game.language == "zh-CN" and game.time == 0 and game.state == "level_select"
        game.handle_events([pygame.event.Event(pygame.QUIT)])
        assert not game.running
        result = {"status": "PASS", "driver": pygame.display.get_driver(),
                  "font": renderer.font_path, "languages": list(TEXT),
                  "checked_texts": len(checked_texts), "screenshots": 16,
                  "checks": "settings language selection, F1 disabled, Chinese glyphs, text bounds, HUD, Boss, results, movement, shooting, pause, restart, quit"}
        (output / "check.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
