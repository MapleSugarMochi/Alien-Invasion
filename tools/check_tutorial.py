"""Windows 真实窗口：公开输入完成双语／改键教程和可恢复的错误路线。"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from game import Game
from preferences import Preferences
from render import Renderer
from settings import WIDTH, HEIGHT
from tools.tutorial_pilot import controls, tap, tutorial_pilot


def button(game, action):
    rect = next(rect for name, _, rect in game.buttons() if name == action)
    game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center),
                        pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center)])


def run(surface, renderer, output, language, remap=False, faults=False):
    preferences = Preferences(language=language)
    if remap:
        preferences.bindings.update(move_up=pygame.K_UP, move_down=pygame.K_DOWN,
                                    move_left=pygame.K_LEFT, move_right=pygame.K_RIGHT,
                                    missile=pygame.K_m, arc=pygame.K_n, support=pygame.K_b, pause=pygame.K_p)
    game = Game("hard", menu=True, preferences=preferences)
    tag = language + ("-faults" if faults else "-remap" if remap else "")
    captured, injected, pending = set(), set(), None
    supply_id = None
    paused = False

    def capture(name):
        renderer.draw(surface, game)
        pygame.display.flip()
        pygame.event.pump()
        pygame.image.save(surface, output / f"{tag}-{name}.png")

    button(game, "level_select")
    capture("levels")
    button(game, "level_1")
    for _ in range(24000):
        pygame.event.pump()
        if game.state == "tutorial_retry":
            assert faults and "combat_death" not in injected
            assert game.tutorial.completed == list(range(1, 8))
            capture("combat-retry")
            button(game, "tutorial_retry")
            injected.add("combat_death")
        if game.state != "playing":
            break
        tutorial = game.tutorial
        stage = tutorial.step
        signature = f"step-{stage}"
        if signature not in captured:
            capture(signature)
            captured.add(signature)
        if not paused and stage == 5 and game.weapons.active == "missile":
            frozen = (game.time, game.weapons.active_until, tutorial.step, tutorial.completed[:])
            game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
            button(game, "settings")
            game.update(3)
            capture("paused-settings")
            button(game, "settings_back")
            assert game.state == "paused"
            game.update(3)
            assert (game.time, game.weapons.active_until, tutorial.step, tutorial.completed) == frozen
            button(game, "resume")
            assert not game.input.fire
            paused = True
        before_retry = tutorial.retries
        handled = False
        if faults and not tutorial.transitioning:
            if stage == 3 and "meteor_destroyed" not in injected and tutorial.meteor:
                controls(game, aim=tutorial.meteor.pos, fire=True)
                handled = True
                pending = "meteor_destroyed"
            elif stage == 4 and "supply_expired" not in injected:
                controls(game)
                if game.pickups:
                    if supply_id is None:
                        supply_id = game.pickups[0].id
                    elif game.pickups[0].id != supply_id:
                        injected.add("supply_expired")
                handled = True
            elif stage in (5, 6) and ("missile_empty" if stage == 5 else "arc_out_of_range") not in injected:
                kind = "missile" if stage == 5 else "arc"
                if game.weapons.charges[kind] == 3 and not tutorial.skill_attempted:
                    controls(game, (1180, 600) if stage == 6 else None, aim=(640, 100))
                    handled = True
                    if stage == 5 or game.player.pos.distance_to((1180, 600)) < 20:
                        tap(game, kind)
                        pending = "missile_empty" if stage == 5 else "arc_out_of_range"
                elif tutorial.skill_attempted:
                    controls(game, aim=(640, 100), fire=stage == 6)
                    handled = True
            elif stage == 8 and "combat_death" not in injected:
                target = next((e for e in game.enemies if e.hp > 0), None)
                controls(game, target.pos if target else game.player.pos)
                handled = True
        if not handled:
            tutorial_pilot(game)
        game.update(1 / 60)
        renderer.feedback(game)
        if pending and tutorial.retries > before_retry:
            injected.add(pending)
            capture(pending + "-retry")
            pending = None
        if game.weapons.active in ("missile", "arc") and game.weapons.active not in captured:
            capture(game.weapons.active)
            captured.add(game.weapons.active)
        if game.support.active and game.support.round_count > 0 and "support" not in captured:
            capture("support")
            captured.add("support")
        if stage == 8 and game.wave.number == 2 and "wave-2" not in captured:
            capture("wave-2")
            captured.add("wave-2")
    assert game.state == "tutorial_complete", (tag, game.state, game.tutorial.step, game.time)
    assert game.tutorial.completed == list(range(1, 9))
    spawns = [e for e in game.journal if e["event"] == "enemy_spawn"]
    # 错误路线保留失败尝试的日志；成功最后一段从其重试检查点开始计算。
    last_combat = max(i for i, e in enumerate(game.journal) if e["event"] == "tutorial_step_start" and e["step"] == 8)
    final_spawns = [e for e in game.journal[last_combat:] if e["event"] == "enemy_spawn"]
    assert Counter(e["kind"] for e in final_spawns) == {"scout": 9, "shooter": 2, "heavy": 1}
    assert not any(e["event"] == "boss_spawn" for e in game.journal)
    assert paused
    if faults:
        assert injected == {"meteor_destroyed", "supply_expired", "missile_empty", "arc_out_of_range", "combat_death"}, injected
    capture("complete")
    result = {"status": "PASS", "language": language, "remapped": remap, "state": game.state,
              "steps": game.tutorial.completed, "time": round(game.time, 3), "retries": game.tutorial.retries,
              "injected_mistakes": sorted(injected), "final_combat_counts": dict(Counter(e["kind"] for e in final_spawns)),
              "pause_settings_frozen": paused, "display_driver": pygame.display.get_driver(),
              "verification": "public injected input; full rules; accelerated wall clock; no progress/health/charge writes",
              "events": game.journal}
    (output / f"{tag}-run.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    button(game, "tutorial_level_2")
    assert (game.state, game.level, game.selected_difficulty) == ("level_select", 2, "hard")
    button(game, "level_2")
    assert game.difficulty.id == "hard" and game.tutorial is None
    assert game.preferences is preferences
    game.handle_events([pygame.event.Event(pygame.QUIT)])
    assert not game.running
    return {k: v for k, v in result.items() if k != "events"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence/tutorial/window")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
        assert pygame.display.get_driver() == "windows", "需要实际 Windows SDL 窗口"
        pygame.display.set_caption("Alien Invasion - tutorial check")
        renderer = Renderer()
        original_text, original_wrap = renderer.text, renderer.wrapped_text

        def checked_text(surface, message, pos, color=(205, 222, 237), anchor="topleft"):
            rect = renderer.font.render(message, True, color).get_rect(**{anchor: pos})
            assert surface.get_rect().contains(rect), f"文字越界：{message}"
            original_text(surface, message, pos, color, anchor)

        def checked_wrap(surface, message, rect, color=(205, 222, 237)):
            height = original_wrap(surface, message, rect, color)
            assert height <= rect.height, f"教学文字被截断：{message}"
            return height

        renderer.text, renderer.wrapped_text = checked_text, checked_wrap
        results = [run(surface, renderer, args.output, "en"),
                   run(surface, renderer, args.output, "zh-CN", remap=True),
                   run(surface, renderer, args.output, "en", faults=True)]
        (args.output / "check.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(results, ensure_ascii=False))
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
