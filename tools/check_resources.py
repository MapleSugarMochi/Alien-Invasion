"""真实显示和音频加载检查；同时检查 PCM 峰值与图集透明度。"""
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
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Alien Invasion — resource check")
        renderer = Renderer()
        atlas = pygame.image.load(str(ROOT / "assets/images/sprite-atlas.png"))
        assert atlas.get_at((0, 0)).a == 0
        game = Game(menu=True)
        renderer.draw(surface, game)
        for index, name in enumerate(renderer.resources.images):
            pos = Vector2(145 + index % 5 * 245, 95 + index // 5 * 190)
            renderer.sprite(surface, name, pos)
            renderer.text(surface, name, pos + Vector2(-45, 75))
        pygame.display.flip()
        pygame.image.save(surface, ROOT / "docs/evidence/p8-resources.png")
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
