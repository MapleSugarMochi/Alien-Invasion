"""教程检查的公开输入策略；只发键鼠事件，不写教学进度或战斗数值。"""
import pygame
from pygame import Vector2


def tap(game, action):
    key = game.preferences.bindings[action]
    game.handle_events([pygame.event.Event(pygame.KEYDOWN, key=key),
                        pygame.event.Event(pygame.KEYUP, key=key)])


def controls(game, destination=None, aim=None, fire=False):
    desired = set()
    if destination is not None:
        delta = Vector2(destination) - game.player.pos
        for component, negative, positive in ((delta.x, "move_left", "move_right"),
                                               (delta.y, "move_up", "move_down")):
            if abs(component) > 6:
                desired.add(game.preferences.bindings[positive if component > 0 else negative])
    events = [pygame.event.Event(pygame.KEYUP, key=key) for key in game.input.keys - desired]
    events += [pygame.event.Event(pygame.KEYDOWN, key=key) for key in desired - game.input.keys]
    position = tuple(aim if aim is not None else game.input.aim)
    events.append(pygame.event.Event(pygame.MOUSEMOTION, pos=position, rel=(0, 0), buttons=(0, 0, 0)))
    if fire != game.input.fire:
        events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN if fire else pygame.MOUSEBUTTONUP,
                                         button=1, pos=position))
    game.handle_events(events)


def tutorial_pilot(game):
    tutorial = game.tutorial
    if tutorial.transitioning:
        controls(game)
        return
    step = tutorial.step
    targets = [e for e in game.enemies if e.hp > 0]
    aim = targets[0].pos if targets else (640, 260)
    if step == 1:
        rect = next(rect for action, _, rect in game.buttons() if action == "tutorial_continue")
        game.handle_events([pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center),
                            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center)])
    elif step == 2:
        controls(game, aim=aim if targets else tutorial.aim_target, fire=tutorial.progress < 3 and bool(targets))
    elif step == 3:
        destination = game.player.pos.copy()
        if game.meteor_warning or tutorial.meteor:
            origin = tutorial.dodge_origin
            destination.update(origin + (180 if origin < 1050 else -180), 560)
        controls(game, destination)
    elif step in (4, 5, 6):
        if game.pickups and not tutorial.skill_attempted:
            controls(game, game.pickups[0].pos, aim)
        else:
            destination = (640, 500) if step == 6 else None
            kind = "missile" if step == 5 else "arc"
            controls(game, destination, aim, step > 4 and game.weapons.active == kind)
            if step > 4 and game.weapons.charges[kind] == 3 and not tutorial.skill_attempted:
                if step == 5 or game.player.pos.distance_to((640, 500)) < 20:
                    tap(game, kind)
    elif step == 7:
        ready = game.energy_units == 1000 and tutorial.progress >= 5
        controls(game, aim=aim, fire=not ready and not game.support.active and not tutorial.support_seen)
        if ready and not tutorial.support_seen:
            tap(game, "support")
    else:
        from tools.play_check import battle_pilot
        battle_pilot(game)
