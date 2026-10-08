"""自动输入的真实规则运行；无跳波、无无敌、无伤害或生命改写。

用于流程回归，不能替代人工手感、声音和难度评价。渲染抽帧且默认
不按墙钟限速，游戏时间仍严格按 1/60 秒推进。
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import platform
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from pygame import Vector2
from game import Game
from localization import DEFAULT_LANGUAGE, TEXT
from render import Renderer
from settings import WIDTH, HEIGHT


def pilot(game):
    # 下半场持续移动避开瞄准弹；只有公开移动/瞄准/开火输入。
    phase = (game.time * 300) % 1840
    desired = Vector2(180 + (phase if phase < 920 else 1840 - phase), 610)
    if game.pickups:
        nearby = [p for p in game.pickups if p.pos.y > 180 and
                  ((p.kind == "health" and game.player.hp < 85) or
                   (p.kind != "health" and game.weapons.charges[p.kind] < 3))]
        if nearby:
            desired = min(nearby, key=lambda p: p.pos.distance_squared_to(game.player.pos)).pos.copy()
    hazards = [(p.pos, p.velocity, p.radius + 14) for p in game.enemy_bullets]
    hazards += [(m.pos, m.velocity, m.radius + 14) for m in game.meteors]
    hazards += [(e.pos, (e.pos - e.previous) * 60, e.radius + 14) for e in game.targets if e.on_screen]
    choices = [Vector2(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1)]

    def cost(direction):
        velocity = direction.normalize() * 340 if direction.length_squared() else Vector2()
        score = (game.player.pos + velocity * .3).distance_to(desired) * .04
        for horizon in (.08, .18, .35, .6):
            position = game.player.pos + velocity * horizon
            if not (25 <= position.x <= 1255 and 90 <= position.y <= 695):
                score += 500
            for pos, motion, radius in hazards:
                margin = position.distance_to(pos + motion * horizon) - radius
                if margin < 0:
                    score += 2000 + (-margin) * 10
                elif margin < 150:
                    score += 2500 / (margin + 10) ** 2
        return score

    move = min(choices, key=cost)
    keys = set()
    if move.x:
        keys.add(game.preferences.bindings["move_right" if move.x > 0 else "move_left"])
    if move.y:
        keys.add(game.preferences.bindings["move_down" if move.y > 0 else "move_up"])
    game.input.keys = keys
    candidates = [e for e in game.targets if e.on_screen and e.damageable]
    if candidates:
        enemy = min(candidates, key=lambda e: (e.kind == "scout", e.pos.distance_squared_to(game.player.pos)))
        lead = (enemy.pos - enemy.previous) * 60 * (enemy.pos.distance_to(game.player.pos) / 900)
        game.input.aim = enemy.pos + lead
    else:
        game.input.aim.update(640, 180)
    game.input.fire = True
    if game.weapons.active == "bullet":
        for kind in ("missile", "arc"):
            key = game.preferences.bindings[kind]
            if game.weapons.charges[kind] == 3:
                game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=key),
                                    pygame.event.Event(pygame.KEYUP, key=key)])
                break
    if game.energy_units == 1000 and not game.support.active:
        key = game.preferences.bindings["support"]
        game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=key),
                            pygame.event.Event(pygame.KEYUP, key=key)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--difficulty", default="standard", choices=("easy", "standard", "hard"))
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, choices=tuple(TEXT))
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--seconds", type=float, default=600)
    parser.add_argument("--mode", choices=("pilot", "idle"), default="pilot")
    parser.add_argument("--realtime", action="store_true", help="每帧显示并按真实墙钟更新，记录 FPS")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence")
    args = parser.parse_args()
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Alien Invasion — gameplay check")
        game, renderer = Game(args.difficulty, args.seed, menu=True, language=args.language), Renderer()
        renderer.draw(surface, game)
        pygame.display.flip()
        game.menu_action("setup")
        game.menu_action(args.difficulty)
        game.menu_action("start")
        # 注入随机源仅为复现随机序列；游戏数值与流程不变。
        game.rng.seed(args.seed)
        frames = 0
        output = args.output
        output.mkdir(parents=True, exist_ok=True)
        last_phase = None
        saved_weapons = set()
        saved_support = False
        clock = pygame.time.Clock()
        wall_start = time.perf_counter()
        compute_times = []
        while game.state == "playing" and game.time < args.seconds:
            dt = clock.tick(60) / 1000 if args.realtime else 1 / 60
            compute_start = time.perf_counter()
            if any(e.type == pygame.QUIT for e in pygame.event.get()):
                break
            if args.mode == "pilot":
                pilot(game)
            game.update(dt)
            renderer.feedback(game)
            frames += 1
            if args.realtime or frames % 30 == 0 or game.phase != last_phase or game.weapons.active not in saved_weapons or (game.support.active and not saved_support):
                renderer.draw(surface, game)
                pygame.display.flip()
                if game.phase != last_phase:
                    pygame.image.save(surface, output / f"{args.difficulty}-{args.mode}-{game.phase}.png")
                last_phase = game.phase
                if game.weapons.active not in saved_weapons:
                    pygame.image.save(surface, output / f"{args.difficulty}-{args.mode}-{game.weapons.active}.png")
                    saved_weapons.add(game.weapons.active)
                if game.support.active and not saved_support and any(r.ids for r in game.support.rounds):
                    pygame.image.save(surface, output / f"{args.difficulty}-{args.mode}-support.png")
                    saved_support = True
            compute_times.append((time.perf_counter() - compute_start) * 1000)
        renderer.draw(surface, game)
        pygame.display.flip()
        pygame.image.save(surface, output / f"{args.difficulty}-{args.mode}-result.png")
        result = {"difficulty": args.difficulty, "language": game.language, "mode": args.mode, "seed": args.seed,
                  "state": game.state, "phase": game.phase, "time": round(game.time, 3),
                  "hp": game.player.hp, "score": game.score, "kills": game.kills,
                  "spawned": len([e for e in game.journal if e["event"] == "enemy_spawn"]),
                  "weapon_activations": [e for e in game.journal if e["event"] == "weapon_activate"],
                  "support_activations": len([e for e in game.journal if e["event"] == "support_start"]),
                  "events": game.journal, "verification": "automatic input; full rules; " + ("real time" if args.realtime else "accelerated wall clock"),
                  "python": sys.version.split()[0], "pygame": pygame.version.ver, "platform": platform.platform(),
                  "wall_seconds": round(time.perf_counter() - wall_start, 3),
                  "frames": frames, "average_fps": round(frames / (time.perf_counter() - wall_start), 2) if args.realtime else None,
                  "compute_ms_p95": round(sorted(compute_times)[int(.95 * (len(compute_times) - 1))], 3) if compute_times else None}
        (output / f"{args.difficulty}-{args.mode}-run.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "events"}, ensure_ascii=False))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
