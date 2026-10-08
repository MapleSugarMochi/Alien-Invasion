"""关卡 1 教学脚本；成功条件来自真实操作结果，不代填充能或战斗能量。"""
from pygame import Vector2

from entities import Enemy, Meteor, Pickup
from settings import (HUD_HEIGHT, HEIGHT, WIDTH, TUTORIAL_ARC_POS,
                      TUTORIAL_ARC_TARGETS, TUTORIAL_PLAYER_POS, TUTORIAL_TRANSITION)
from waves import WaveController
from weapons import WeaponController


class TutorialController:
    def __init__(self, game):
        self.step = 1
        self.completed = []
        self.retries = 0
        self.transition_until = 0.0
        self.notice = ""
        self.enter(game)

    @property
    def transitioning(self):
        return bool(self.transition_until)

    def clear_scene(self, game):
        game.clear_battle_resources()
        game.enemies.clear()
        game.meteors.clear()
        game.projectiles.clear()
        game.enemy_bullets.clear()
        game.effects.clear()
        game.arc_effects.clear()
        game.sound_events.clear()
        game.boss = None

    def enter(self, game, retry=False):
        self.clear_scene(game)
        game.weapons = WeaponController()
        game.player.pos.update(TUTORIAL_ARC_POS if self.step == 6 else TUTORIAL_PLAYER_POS)
        game.player.previous = game.player.pos.copy()
        game.player.hp = 75 if self.step == 4 else 100
        game.player.invulnerable_until = 0
        game.input.aim.update(640, 180)
        game.player.direction.update(0, -1)
        game.next_drop = game.next_meteor = float("inf")
        game.phase = "tutorial"
        game.state = "playing"
        self.transition_until = 0
        self.started_at = game.time
        self.progress_at = game.time
        self.progress = 0
        self.aim_origin = game.input.aim.copy()
        self.aim_seen = False
        self.aim_target = Vector2(480, 260)
        self.released_at = None
        self.last_fire = game.time
        self.skill_attempted = self.skill_success = False
        self.support_seen = self.support_ended = False
        self.support_hits = 0
        self.hints_seen = set()
        self.meteor = None
        self.meteor_contact = False
        self.dodge_shift = 0
        self.next_trial = game.time + .8
        if retry:
            game.score, game.kills = self.checkpoint
        else:
            self.checkpoint = (game.score, game.kills)
            self.notice = "tutorial_reset"
        if self.step == 8:
            game.wave = WaveController(1, game.time, game.level_config.waves)
            game.phase = "tutorial_combat"
            game.next_drop = game.time + 7
        game.record("tutorial_step_start", step=self.step, retry=retry, hp=game.player.hp)

    def retry(self, game, reason):
        # 重试恢复本步检查点；陨石已完成的子任务保留，统计不会被重复刷取。
        saved = self.progress if self.step == 3 else 0
        self.retries += 1
        game.record("tutorial_retry", step=self.step, reason=reason, count=self.retries)
        self.enter(game, retry=True)
        self.progress = saved
        self.notice = reason
        self.transition_until = game.ui_time + TUTORIAL_TRANSITION
        self.pending_step = self.step

    def complete(self, game):
        if self.transitioning or self.step in self.completed:
            return
        self.completed.append(self.step)
        game.record("tutorial_step_end", step=self.step)
        self.notice = "tutorial_step_done"
        self.transition_until = game.ui_time + TUTORIAL_TRANSITION
        self.pending_step = self.step + 1
        game.input.clear()
        game.commands.clear()

    def advance_transition(self, game):
        if game.ui_time + 1e-9 < self.transition_until:
            return
        self.transition_until = 0
        game.input.clear()
        game.commands.clear()
        if self.pending_step > 8:
            game.record("tutorial_complete", steps=list(self.completed), retries=self.retries)
            game.finish("tutorial_complete")
        elif self.pending_step != self.step:
            self.step = self.pending_step
            self.enter(game)

    def objective(self, game, name):
        self.progress_at = game.time
        game.record("tutorial_objective", step=self.step, objective=name, progress=self.progress)

    def continue_intro(self, game):
        if self.step == 1 and not self.transitioning:
            self.objective(game, "movement_instructions_read")
            self.complete(game)

    def spawn_target(self, game, kind, pos, sway=False):
        enemy = Enemy.create(game.next_id(), kind, pos, game.difficulty, game.time)
        enemy.training = enemy.entered = True
        enemy.training_sway = sway
        enemy.next_shot = float("inf")
        game.enemies.append(enemy)
        game.record("tutorial_target", step=self.step, id=enemy.id, kind=kind)
        return enemy

    def fill_targets(self, game, kind, positions, sway=False):
        alive = [e for e in game.enemies if e.hp > 0]
        occupied = {round(e.origin_x) for e in alive}
        for pos in positions:
            if len(alive) >= len(positions):
                break
            if pos[0] not in occupied:
                alive.append(self.spawn_target(game, kind, pos, sway))

    def supply(self, game, kind):
        if game.pickups:
            return
        x = game.player.pos.x + (140 if game.player.pos.x < WIDTH - 200 else -140)
        y = max(230, min(580, game.player.pos.y - 100))
        pickup = Pickup(game.next_id(), Vector2(x, y), game.time, kind)
        game.pickups.append(pickup)
        game.record("tutorial_supply", step=self.step, kind=kind, id=pickup.id)

    def on_pickup(self, game, pickup):
        expected = {4: "health", 5: "missile", 6: "arc"}.get(self.step)
        if expected == pickup.kind:
            self.progress += 1
            self.objective(game, "pickup_" + pickup.kind)

    def on_kill(self, game, target, source):
        if not target.training:
            return
        if self.step == 2 and source == "bullet":
            self.progress += 1
            self.objective(game, "bullet_target")
        elif self.step == 5 and source == "missile":
            self.skill_success = True
            self.objective(game, "missile_hit")
        elif self.step == 7:
            if source == "bullet" and target.kind == "heavy":
                self.progress += 1
                self.objective(game, "energy_target")
            elif source == "support":
                self.support_hits += 1
                self.objective(game, "support_hit")

    def on_activation(self, game, kind):
        if (self.step, kind) in ((5, "missile"), (6, "arc")):
            self.skill_attempted = True
            self.objective(game, "activate_" + kind)

    def on_arc(self, game, targets):
        if self.step == 6 and len({t.id for t in targets}) == 3:
            self.skill_success = True
            self.objective(game, "arc_three_targets")

    def update_meteor(self, game):
        if self.meteor:
            self.dodge_shift = max(self.dodge_shift, abs(game.player.pos.x - self.dodge_origin))
            if self.meteor_contact:
                self.retry(game, "tutorial_meteor_hit")
            elif self.meteor.hp <= 0:
                self.retry(game, "tutorial_meteor_shot")
            elif self.meteor.pos.y - self.meteor.radius > HEIGHT:
                if self.dodge_shift < 70:
                    self.retry(game, "tutorial_meteor_move")
                else:
                    self.progress += 1
                    self.objective(game, "meteor_dodged")
                    self.meteor = None
                    self.next_trial = game.time + .8
                    if self.progress == 3:
                        self.complete(game)
            return
        if game.meteor_warning:
            self.dodge_shift = max(self.dodge_shift, abs(game.player.pos.x - self.dodge_origin))
            due, x, radius = game.meteor_warning
            if game.time + 1e-9 >= due:
                self.meteor = Meteor(game.next_id(), Vector2(x, HUD_HEIGHT - radius))
                game.meteors.append(self.meteor)
                game.meteor_warning = None
                game.record("meteor_spawn")
        elif game.time + 1e-9 >= self.next_trial:
            self.dodge_origin = game.player.pos.x
            self.dodge_shift = 0
            game.meteor_warning = (game.time + .6, max(22, min(WIDTH - 22, self.dodge_origin)), 22)
            game.record("meteor_warning")

    def update_combat(self, game):
        # 只在首次遇到相应情境时提示，不弹窗也不暂停实战。
        hints = (("low_hp", game.player.hp <= 50, "tutorial_combat_health_hint"),
                 ("enemy_fire", bool(game.enemy_bullets), "tutorial_combat_fire_hint"),
                 ("weapon_ready", any(n == 3 for n in game.weapons.charges.values()), "tutorial_combat_skill_hint"),
                 ("support_ready", game.energy_units == 1000, "tutorial_combat_support_hint"))
        for name, ready, key in hints:
            if ready and name not in self.hints_seen:
                self.hints_seen.add(name)
                self.notice = key
                self.progress_at = game.time
                game.record("tutorial_hint", step=8, hint=name)
                break
        if game.time + 1e-9 >= game.next_drop:
            game.drop_supply()
        if game.wave.number == 2:
            if game.meteor_warning and game.time + 1e-9 >= game.meteor_warning[0]:
                _, x, _ = game.meteor_warning
                game.meteors.append(Meteor(game.next_id(), Vector2(x, HUD_HEIGHT - 22)))
                game.meteor_warning = None
                game.next_meteor = game.time + 8
                game.record("meteor_spawn")
            elif not game.meteor_warning and game.time + 1e-9 >= game.next_meteor - .6 and not game.meteors:
                game.meteor_warning = (max(game.time + .6, game.next_meteor), game.rng.uniform(22, WIDTH - 22), 22)
                game.record("meteor_warning")
        if game.phase == "tutorial_rest":
            if game.time + 1e-9 < game.phase_until:
                return
            game.wave = WaveController(2, game.time, game.level_config.waves)
            game.phase = "tutorial_combat"
            game.next_meteor = game.time + 8
        enemy = game.wave.update(game.time, len(game.enemies), game.difficulty, game._entity_id + 1)
        if enemy:
            game.next_id()
            game.enemies.append(enemy)
            game.record("enemy_spawn", id=enemy.id, kind=enemy.kind, wave=game.wave.number)
        if not game.wave.queue and not game.enemies:
            game.record("wave_end", wave=game.wave.number)
            if game.wave.number == 1:
                game.phase = "tutorial_rest"
                game.phase_until = game.time + 3
            else:
                self.objective(game, "two_waves_survived")
                self.complete(game)

    def update(self, game):
        if self.transitioning or game.state != "playing":
            return
        if game.player.hp <= 0:
            game.state = "tutorial_retry"
            game.clear_battle_resources()
            return
        if self.step == 2:
            if game.enemies:
                self.aim_target = game.enemies[0].pos.copy()
            self.aim_seen |= (game.input.aim.distance_to(self.aim_origin) >= 80 and
                              game.input.aim.distance_to(self.aim_target) < 80)
            if self.progress < 3 and not game.enemies:
                self.spawn_target(game, "scout", ((480, 640, 800)[self.progress], 260))
            if self.progress >= 3 and not game.input.fire:
                if self.released_at is None:
                    self.released_at = game.time
            else:
                self.released_at = None
            if (self.progress >= 3 and self.aim_seen and self.released_at is not None and
                    game.time - self.released_at >= .4 and game.time - self.last_fire >= .4):
                self.objective(game, "release_fire")
                self.complete(game)
        elif self.step == 3:
            self.update_meteor(game)
        elif self.step == 4:
            if self.progress and game.player.hp == 100:
                self.complete(game)
            else:
                self.supply(game, "health")
        elif self.step in (5, 6):
            kind = "missile" if self.step == 5 else "arc"
            if not self.skill_attempted:
                if game.weapons.charges[kind] < 3:
                    self.supply(game, kind)
                else:
                    positions = ((480, 260), (800, 260)) if self.step == 5 else TUTORIAL_ARC_TARGETS
                    self.fill_targets(game, "scout" if self.step == 5 else "shooter", positions, self.step == 5)
            elif game.weapons.active == "bullet":
                if self.skill_success:
                    self.objective(game, "weapon_restored")
                    self.complete(game)
                else:
                    self.retry(game, "tutorial_skill_retry")
            elif not self.skill_success:
                positions = ((480, 260), (800, 260)) if self.step == 5 else TUTORIAL_ARC_TARGETS
                self.fill_targets(game, "scout" if self.step == 5 else "shooter", positions, self.step == 5)
        elif self.step == 7:
            if self.support_ended:
                if self.support_hits and game.support.round_count == 5:
                    self.complete(game)
                else:
                    self.retry(game, "tutorial_support_retry")
            elif self.support_seen or (self.progress >= 5 and game.energy_units == 1000):
                self.fill_targets(game, "scout", ((480, 260), (640, 260), (800, 260)))
            elif not game.enemies:
                self.spawn_target(game, "heavy", (640, 260))
        elif self.step == 8:
            self.update_combat(game)

    def lines(self, game):
        """由当前真实状态选择提示；绑定名在显示时解析，设置回来立即更新。"""
        tr = game.text
        keys = {action: game.binding_name(action) for action in game.preferences.bindings}
        if self.step == 1:
            return [tr("tutorial_move", **keys), tr("tutorial_move_note")]
        if self.step == 2:
            return [tr("tutorial_shoot" if self.progress < 3 else
                       "tutorial_aim" if not self.aim_seen else "tutorial_release"),
                    tr("tutorial_targets", count=min(3, self.progress), total=3)]
        if self.step == 3:
            return [tr("tutorial_dodge"), tr("tutorial_dodges", count=self.progress)]
        if self.step == 4:
            return [tr("tutorial_health"), tr("tutorial_supply_types")]
        if self.step in (5, 6):
            kind = "missile" if self.step == 5 else "arc"
            key = "tutorial_charge" if game.weapons.charges[kind] < 3 and not self.skill_attempted else "tutorial_use_" + kind
            if self.skill_attempted and self.skill_success:
                key = "tutorial_wait_weapon"
            return [tr(key, weapon=tr(kind), binding=keys[kind]),
                    tr("tutorial_missile_note" if self.step == 5 else "tutorial_arc_note")]
        if self.step == 7:
            return [tr("tutorial_support_active" if game.support.active else
                       "tutorial_support_ready" if game.energy_units == 1000 and self.progress >= 5 else "tutorial_energy", binding=keys["support"]),
                    tr("tutorial_support_rounds", count=game.support.round_count) if self.support_seen else tr("tutorial_energy_note")]
        return [tr("tutorial_combat_note"), tr("tutorial_combat_wave", number=game.wave.number)]
