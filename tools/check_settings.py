"""真实窗口验证设置、改键、共享键、柔和闪烁、拖动、重置与磁盘重载。"""
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from game import Game
from preferences import DEFAULT_BINDINGS, Preferences
from render import Renderer
from settings import HEIGHT, WIDTH


def main():
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        assert pygame.display.get_driver() == "windows", "本检查需要 Windows 真实窗口"
        pygame.display.set_caption("Alien Invasion - settings check")
        renderer = Renderer()
        output = ROOT / "docs/evidence/settings"
        output.mkdir(parents=True, exist_ok=True)
        original_text = renderer.text
        text_count = 0

        def checked_text(surface, message, pos, color=(205, 222, 237), anchor="topleft"):
            nonlocal text_count
            rect = renderer.font.render(message, True, color).get_rect(**{anchor: pos})
            assert surface.get_rect().contains(rect), f"文字溢出：{message} {rect}"
            text_count += 1
            original_text(surface, message, pos, color, anchor)

        renderer.text = checked_text

        def click(game, pos):
            game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos),
                                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos)])

        def button(game, action):
            click(game, next(rect.center for name, _, rect in game.buttons() if name == action))

        def capture(game, name):
            renderer.feedback(game)
            renderer.draw(surface, game)
            for _, label, rect in game.buttons():
                assert rect.inflate(-16, -4).contains(renderer.font.render(label, True, (255, 255, 255)).get_rect(center=rect.center)), label
            for action, _, label, rect in game.control_rows():
                if game.state in ("setup", "settings"):
                    message = game.text("key_prompt") if action == game.editing_binding else label
                    assert rect.inflate(-12, -4).contains(renderer.font.render(message, True, (255, 255, 255)).get_rect(center=rect.center)), message
            pygame.display.flip()
            pygame.event.pump()
            pygame.image.save(surface, output / f"{name}.png")

        def rebind(game, action, key):
            rect = next(rect for name, _, _, rect in game.control_rows() if name == action)
            click(game, rect.center)
            assert game.editing_binding == action
            capture(game, "waiting-key")
            game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=key),
                                pygame.event.Event(pygame.KEYUP, key=key)])
            assert game.preferences.bindings[action] == key

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            game = Game(menu=True, preferences=Preferences.load(path))
            button(game, "settings")
            assert [name for name, _, _ in game.buttons()] == [
                "language_en", "language_zh-CN", "reset_keys", "settings_back"]
            capture(game, "en-default")
            assert not any(name in ("easy", "standard", "hard") for name, _, _ in game.buttons())
            button(game, "language_zh-CN")
            capture(game, "zh-CN-default")
            rebind(game, "move_right", pygame.K_z)
            rebind(game, "missile", pygame.K_z)
            game.ui_time = 0
            capture(game, "conflict-soft")
            rect = next(rect for name, _, _, rect in game.control_rows() if name == "missile")
            pixel = (rect.left + 12, rect.centery)
            soft = surface.get_at(pixel)
            game.update(2)
            assert game.time == 0
            capture(game, "conflict-strong")
            strong = surface.get_at(pixel)
            assert 0 < strong.r - soft.r < 25, (soft, strong)
            rect = game.sliders()[0][1]
            game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center),
                                pygame.event.Event(pygame.MOUSEMOTION, pos=(rect.left + 110, rect.centery)),
                                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(rect.left + 110, rect.centery))])
            assert game.sfx_volume == .25
            capture(game, "volume-quarter")
            before = (game.language, game.sfx_volume, game.music_volume, game.preferences.bindings.copy())
            click(game, (492, 649))  # 已删除的恢复全部按钮原点击区域。
            assert (game.language, game.sfx_volume, game.music_volume, game.preferences.bindings) == before
            button(game, "settings_back")
            game = Game(menu=True, preferences=Preferences.load(path))
            assert game.language == "zh-CN" and game.sfx_volume == .25
            assert game.preferences.conflicts() == {"move_right", "missile"}
            button(game, "setup")
            button(game, "hard")
            capture(game, "choose-difficulty")
            button(game, "start")
            game.weapons.charges["missile"] = 3
            old = game.player.pos.copy()
            game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z),
                                pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(640, 180))])
            game.update(.1)
            assert game.player.pos.x > old.x and game.weapons.active == "missile"
            capture(game, "remapped-hud")
            game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)])
            button(game, "settings")
            frozen = game.time
            game.update(1)
            assert game.time == frozen
            button(game, "reset_keys")
            assert game.preferences.bindings == DEFAULT_BINDINGS and not game.preferences.conflicts()
            assert game.language == "zh-CN" and game.sfx_volume == .25
            capture(game, "keys-reset")
            button(game, "settings_back")
            assert game.state == "paused"
            button(game, "restart")
            assert game.state == "setup"
            button(game, "easy")
            button(game, "start")
            assert game.difficulty.id == "easy"
            game.pause()
            button(game, "settings")
            assert game.language == "zh-CN" and game.sfx_volume == .25
            capture(game, "settings-final")
            game.handle_events([pygame.event.Event(pygame.QUIT)])
            assert not game.running
        result = {"status": "PASS", "driver": pygame.display.get_driver(), "font": renderer.font_path,
                  "checked_texts": text_count, "conflict_pixel_red": [soft.r, strong.r],
                  "checks": "two-column table, capture, duplicate actions, soft 4s pulse, sliders, persistence, keys-only reset, removed-button area inactive, paused settings, new-game difficulty, HUD, quit"}
        (output / "check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
