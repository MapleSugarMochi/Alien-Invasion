"""真实显示和音频加载检查；核对独立精灵透明度、边界和 PCM 峰值。"""
import argparse
from array import array
import os
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from pygame import Vector2
from game import Game
from render import Renderer
from settings import WIDTH, HEIGHT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Alien Invasion — resource check")
        renderer = Renderer()
        assert renderer.resources.background.get_width() >= WIDTH
        for name in renderer.resources.sprite_sizes:
            source = pygame.image.load(str(ROOT / f"assets/images/craft/{name}.png"))
            assert source.get_flags() & pygame.SRCALPHA, name
            assert source.get_at((0, 0)).a == 0, name
            bounds = source.get_bounding_rect(min_alpha=8)
            assert bounds.width and bounds.height and bounds.left > 0 and bounds.top > 0, name
            assert bounds.right < source.get_width() and bounds.bottom < source.get_height(), name
        for name, image in renderer.resources.images.items():
            assert image.get_at((0, 0)).a == 0 and image.get_bounding_rect(min_alpha=8).width, name
        renderer.resources.scaled("missile", (30, 30))
        game = Game(menu=True, level=2)
        renderer.draw(surface, game)
        surface.blit(renderer.space, (0, 0))
        renderer.text(surface, "ALIEN INVASION / RESOURCES", (24, 24))
        for index, name in enumerate(renderer.resources.images):
            # 宽母舰单独占一行；不会与其他精灵展示相互遮挡。
            if name == "boss":
                pos = Vector2(640, 365)
            else:
                slot = index if index < 4 else index - 1
                pos = Vector2(135 + slot % 5 * 250, 140 if slot < 5 else 540 if slot < 10 else 650)
            renderer.sprite(surface, name, pos)
            renderer.label(surface, name, pos + Vector2(0, 100 if name == "boss" else 45), anchor="midtop")
        pygame.display.flip()
        pygame.image.save(surface, args.output / "resources.png")
        peaks = {}
        for name in renderer.resources.sound_names:
            with wave.open(str(ROOT / f"assets/audio/sfx/{name}.wav"), "rb") as audio:
                assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 44100)
                samples = array("h", audio.readframes(audio.getnframes()))
                peak = max(abs(s) for s in samples) / 32767
                assert 0 < peak <= .33
                peaks[name] = round(peak, 3)
            renderer.resources.play(name)
            pygame.event.pump()
            pygame.time.wait(550)
        game.menu_action("settings")
        for attribute, value in (("sfx_volume", .35), ("music_volume", .45)):
            rect = next(rect for name, rect in game.sliders() if name == attribute)
            position = (round(rect.left + rect.width * value), rect.centery)
            game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=position),
                                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=position)])
        renderer.feedback(game)
        assert (game.sfx_volume, game.music_volume) == (.35, .45)
        if renderer.resources.audio_available:
            renderer.resources.play("bullet")
            assert abs(renderer.resources.channels["bullet"].get_volume() - .35) < .01
            assert abs(pygame.mixer.music.get_volume() - .45) < .01
        game.menu_action("settings_back")
        game.start_session("standard")
        assert (game.sfx_volume, game.music_volume) == (.35, .45)
        renderer.draw(surface, game)
        print("PASS: sprites, alpha, sound formats/peaks, independent volume, no-BGM; font", renderer.font_path,
              "audio", renderer.resources.audio_available, "peaks", peaks)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
