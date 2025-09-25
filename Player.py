import random
import time
import pygame
from Actor import Actor, MovementState
from Entity import Entity
from NonPlayer import NonPlayer
from Block import BreakableBlock
from Helpers import MovementDirection, load_sprite_sheets, display_text
from VisualEffects import VisualEffect


class Player(Actor):
    ATTACK_PUSHBACK = 0.2
    VELOCITY_TARGET = 0.5
    VELOCITY_DRAG = 0.9
    MULTIPLIER_TELEPORT = 384
    TELEPORT_COOLDOWN = 3
    TELEPORT_DELAY = 0.4
    TELEPORT_EFFECT_TRAIL = 0.05
    BLOCK_COOLDOWN = 3
    BLOCK_EFFECT_TIME = 2
    BULLET_TIME_COOLDOWN = 3
    BULLET_TIME_ACTIVE = 2

    def __init__(self, level, controller, x, y, sprite_master, audios, difficulty, block_size, can_shoot=False, sprite=None, retro_sprite=None, proj_sprite=None):
        super().__init__(level, controller, x, y, sprite_master, audios, difficulty, block_size, can_shoot=can_shoot, sprite=sprite, proj_sprite=proj_sprite, name="Player")
        self.sprites_set = (self.sprites.copy(), load_sprite_sheets("Sprites", retro_sprite, sprite_master, direction=True, grayscale=True) if retro_sprite is not None else None)
        self.is_retro = False
        if self.level.grayscale:
            self.toggle_retro()
            self.update_sprite(1)
        self.cooldowns.update({"teleport": 0.0, "teleport_delay": 0.0, "teleport_effect_trail": 0.0, "block": 0.0, "block_attempt": 0.0, "blocking_effect": 0.0, "bullet_time": 0.0, "bullet_time_active": 0.0})
        self.cached_cooldowns = self.cooldowns.copy()
        self.target_vel = Player.VELOCITY_TARGET
        self.drag_vel = Player.VELOCITY_DRAG
        self.can_open_doors = True
        self.can_move_blocks = True
        self.can_block = True
        self.is_blocking = False
        self.can_wall_jump = True
        self.can_teleport = False
        self.can_bullet_time = False
        self.is_slow_time = False
        self.can_resize = False
        self.can_heal = True
        self.max_jumps = 2
        self.attack_damage *= 2
        self.max_hp = self.hp = self.cached_hp = 100 / self.difficulty
        self.been_hit_this_level = False
        self.been_seen_this_level = False
        self.deaths_this_level = 0
        self.kills_this_level = 0

    def toggle_retro(self) -> None:
        if self.is_retro:
            self.sprites = self.sprites_set[0]
            self.is_retro = False
        else:
            self.sprites = self.sprites_set[1]
            self.is_retro = True

    def save(self) -> dict:
        data = super().save()
        data[self.name].update({"can_teleport": self.can_teleport,
                                "can_bullet_time": self.can_bullet_time,
                                "been_hit_this_level": self.been_hit_this_level,
                                "been_seen_this_level": self.been_seen_this_level,
                                "deaths_this_level": self.deaths_this_level,
                                "kills_this_level": self.kills_this_level})
        return data

    def load(self, ent) -> None:
        self.load_attribute(ent, "can_teleport")
        self.load_attribute(ent, "can_bullet_time")
        self.load_attribute(ent, "been_hit_this_level")
        self.load_attribute(ent, "been_seen_this_level")
        self.load_attribute(ent, "deaths_this_level")
        self.load_attribute(ent, "kills_this_level")
        super().load(ent)

    def set_difficulty(self, scale) -> None:
        self.difficulty = scale
        self.max_hp /= scale
        self.hp /= scale
        self.attack_damage /= scale

    def toggle_crouch(self) -> None:
        self.is_crouching = not self.is_crouching

    def stop(self) -> None:
        self.should_move_horiz = False

    def block(self) -> None:
        if self.can_block and self.cooldowns["block"] <= 0 and self.cooldowns["blocking_effect"] <= 0:
            self.cooldowns["blocking_effect"] = Player.BLOCK_EFFECT_TIME
            self.cooldowns["block"] = Player.BLOCK_COOLDOWN
            if self.level.visual_effects_manager.images.get("BLOCKSHIELD") is not None:
                scale = max(self.rect.width, self.rect.height)
                self.active_visual_effects["blocking_effect"] = VisualEffect(self, self.level.visual_effects_manager.images["BLOCKSHIELD"], alpha=128, scale=(scale, scale), linked_to_source=True)

    def get_hit(self, ent) -> None:
        if self.controller.should_scroll_to_point is not None:
            return
        else:
            if isinstance(ent, NonPlayer) and self.cooldowns["blocking_effect"] > 0:
                self.cooldowns["blocking_effect"] = 0
            else:
                self.been_hit_this_level = True
                super().get_hit(ent)

    def move_left(self) -> None:
        self.should_move_horiz = True
        if self.direction != MovementDirection.LEFT:
            self.direction = self.facing = MovementDirection.LEFT

    def move_right(self) -> None:
        self.should_move_horiz = True
        if self.direction != MovementDirection.RIGHT:
            self.direction = self.facing = MovementDirection.RIGHT

    def revert(self) -> int:
        start = time.perf_counter_ns()
        text = ["Careful!", "You died.", "Watch out!", "OUCH!", "Don't try that again!", "Agent? Agent?!", "Initiating respawn...", "Reverting time..."]
        display_text(text[random.randrange(len(text))], self.controller, min_pause_time=0, should_sleep=True)
        self.should_move_vert = False
        self.rect.x, self.rect.y = self.cached_x, self.cached_y
        self.hp = self.cached_hp
        self.size = self.cached_size
        self.size_target = self.cached_size_target
        self.cooldowns = self.cached_cooldowns
        self.deaths_this_level += 1
        return (time.perf_counter_ns() - start) // 1000000

    def teleport(self) -> None:
        if self.can_teleport and self.cooldowns["teleport"] <= 0:
            for i in range(int(Player.VELOCITY_TARGET * Player.MULTIPLIER_TELEPORT) + 1, 0, -1):
                cast = Entity(self.level, self.controller, self.rect.x + (self.direction * i), self.rect.y, self.rect.width, self.rect.height - 1)
                collision = False
                for ent in self.level.get_entities_in_range((cast.rect.x, cast.rect.y)):
                    if pygame.sprite.collide_rect(cast, ent):
                        collision = True
                        break
                if not collision:
                    self.teleport_distance = self.direction * i
                    self.cooldowns["teleport_delay"] = Player.TELEPORT_DELAY
                    self.cooldowns["teleport"] = Player.TELEPORT_DELAY
                    return

    def attack(self) -> None:
        if self.state in [MovementState.IDLE, MovementState.CROUCH, MovementState.RUN, MovementState.FALL, MovementState.JUMP, MovementState.DOUBLE_JUMP, MovementState.IDLE_ATTACK, MovementState.CROUCH_ATTACK, MovementState.RUN_ATTACK, MovementState.FALL_ATTACK, MovementState.JUMP_ATTACK, MovementState.DOUBLE_JUMP_ATTACK]:
            self.is_attacking = True
            for ent in self.level.get_entities_in_range((self.rect.x, self.rect.y)):
                if isinstance(ent, NonPlayer) and ent.is_hostile and pygame.sprite.collide_rect(self, ent) and self.facing == (MovementDirection.RIGHT if ent.rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT):
                    ent.get_hit(self)
                    if ent.patrol_path is not None:
                        ent.push_x -= self.direction * int(Player.ATTACK_PUSHBACK)
                    self.play_attack_audio("ATTACK_MELEE")
                elif isinstance(ent, BreakableBlock) and pygame.sprite.collide_rect(self, ent):
                    ent.get_hit(self)
                    self.play_attack_audio("ATTACK_MELEE")

    def bullet_time(self) -> None:
        if self.can_bullet_time:
            if self.is_slow_time:
                self.is_slow_time = False
                self.cooldowns["bullet_time_active"] = 0
                self.cooldowns["bullet_time"] = min(Player.BULLET_TIME_COOLDOWN, self.cooldowns["bullet_time"])
            elif self.cooldowns["bullet_time"] <= 0:
                self.is_slow_time = True
                self.cooldowns["bullet_time_active"] = Player.BULLET_TIME_ACTIVE
                self.cooldowns["bullet_time"] = Player.BULLET_TIME_COOLDOWN
                if self.audios.get("BULLET_TIME") is not None:
                    active_audio_channel = pygame.mixer.find_channel()
                    if active_audio_channel is not None:
                        active_audio_channel.play(self.audios["BULLET_TIME"][random.randrange(len(self.audios["BULLET_TIME"]))])
                        active_audio_channel.set_volume(self.controller.master_volume["player"])

    def get_triggers(self) -> list:
        fired_triggers = 0
        next_level = None
        for trigger in self.level.triggers:
            if pygame.sprite.collide_rect(self, trigger):
                result = trigger.collide(self)
                fired_triggers += result[0]
                next_level = result[1]
                if trigger.fire_once:
                    self.level.queue_purge(trigger)
        return [fired_triggers, next_level]

    def loop(self, dtime) -> list:
        if self.teleport_distance != 0:
            self.animation_count += dtime
            if self.cooldowns["teleport_delay"] <= 0:
                self.move(self.teleport_distance, 0)
                self.cooldowns["teleport_effect_trail"] = Player.TELEPORT_EFFECT_TRAIL
                if self.level.visual_effects_manager.images.get("DASHCLOUD") is not None:
                    self.active_visual_effects["teleport_effect_trail"] = VisualEffect(self, self.level.visual_effects_manager.images["DASHCLOUD"], direction=str(self.direction), alpha=64, offset=(self.rect.width // 2, 0), scale=(abs(self.teleport_distance), self.rect.height * 0.8))
                self.teleport_distance = 0
            self.update_cooldowns(dtime)
            self.update_state()
        else:
            if self.is_slow_time and self.cooldowns["bullet_time_active"] <= 0:
                self.is_slow_time = False
            super().loop(dtime)

        return self.get_triggers()
