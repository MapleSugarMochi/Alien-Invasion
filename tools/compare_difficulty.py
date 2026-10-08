"""相同第四波的实际输入运行画面，不跳波或改写对象。"""
import os
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from game import Game
from render import Renderer
from play_check import pilot


def main():
    pygame.init()
    try:
        surface = pygame.display.set_mode((1280, 720))
        pygame.display.set_caption("Alien Invasion — difficulty comparison")
        renderer = Renderer()
        records = []
        for difficulty in ("easy", "standard", "hard"):
            game = Game(difficulty, seed=5)
            wave_start = None
            while game.state == "playing" and game.time < 120:
                pygame.event.pump()
                pilot(game)
                game.update(1 / 60)
                renderer.feedback(game)
                if game.wave.number == 4 and wave_start is None:
                    wave_start = game.time
                if wave_start is not None and game.time >= wave_start + 3:
                    break
            assert game.state == "playing" and game.wave.number == 4
            renderer.draw(surface, game)
            pygame.display.flip()
            pygame.image.save(surface, ROOT / f"docs/evidence/{difficulty}-wave4.png")
            records.append({"difficulty": difficulty, "time": round(game.time, 3), "wave": 4,
                            "enemy_cap": game.difficulty.enemy_cap, "meteor_interval": game.difficulty.meteor_interval,
                            "meteor_cap": game.difficulty.meteor_cap, "hp_multiplier": game.difficulty.health,
                            "move_multiplier": game.difficulty.movement,
                            "bullet_speed_multiplier": game.difficulty.bullet_speed,
                            "fire_interval_multiplier": game.difficulty.fire_interval,
                            "damage_multiplier": game.difficulty.damage,
                            "screen_enemies": len(game.enemies), "bullets": len(game.enemy_bullets)})
        (ROOT / "docs/evidence/difficulty-comparison.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
        print("PASS: real-input wave 4 comparison", json.dumps(records))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
