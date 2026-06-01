from __future__ import annotations
from typing import TYPE_CHECKING
import random
import time
import pygame
from Actor import Actor, MovementState
from Entity import Entity
from NonPlayer import NonPlayer
from Block import BreakableBlock
from Helpers import (
    MovementDirection,
    load_sprite_sheets,
    display_text,
    RUMBLE_EFFECT_LOW,
    RUMBLE_EFFECT_DURATION,
)
from SimpleVFX.SimpleVFX import VisualEffect, ImageDirection

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level


class Player(Actor):
    ATTACK_PUSHBACK       = 200
    VELOCITY_TARGET       = 500
    ACCEL_MAX_TIME        = 0.5
    MULTIPLIER_TELEPORT   = 0.432
    TELEPORT_COOLDOWN     = 3
    TELEPORT_DELAY        = 0.35
    TELEPORT_EFFECT_TRAIL = 0.05
    BLOCK_COOLDOWN        = 3
    BLOCK_EFFECT_TIME     = 2
    BULLET_TIME_COOLDOWN  = 3
    BULLET_TIME_ACTIVE    = 2

    def __init__(
            self:          Player,
            level:         Level,
            controller:    Controller,
            x:             float,
            y:             float,
            sprite_master: dict,
            audios:        dict,
            difficulty:    float,
            block_size:    float,
            can_shoot:     bool       = False,
            sprite:        str | None = None,
            retro_sprite:  str | None = None,
            proj_sprite:   str | None = None,
    ) -> None:
        """Initialize the player actor, its retro sprite set, abilities, and cooldowns."""
        super().__init__(
            level,
            controller,
            x,
            y,
            sprite_master,
            audios,
            difficulty,
            block_size,
            can_shoot   = can_shoot,
            sprite      = sprite,
            proj_sprite = proj_sprite,
            name        = "Player",
        )
        self.sprites_set = (self.sprites.copy(), load_sprite_sheets("Sprites", retro_sprite, sprite_master, direction = True, retro = True) if retro_sprite else None)
        self.is_retro    = False
        if self.level.retro:
            self.toggle_retro()
            self.update_sprite()
        self.abilities["can_open_doors"] = self.abilities["can_move_blocks"] = self.abilities["can_heal"] = True
        self.cooldowns.update({"teleport": 0.0, "teleport_delay": 0.0, "teleport_effect_trail": 0.0, "block": 0.0, "block_attempt": 0.0, "blocking_effect": 0.0, "bullet_time": 0.0, "bullet_time_active": 0.0, "dead": 0.0})
        self.cached_cooldowns      = self.cooldowns.copy()
        self.target_vel            = Player.VELOCITY_TARGET
        self.x_accel_max_time      = Player.ACCEL_MAX_TIME
        self.is_blocking           = False
        self.is_slow_time          = False
        self.attack_damage         *= 2
        self.max_hp = self.hp      = 100 / self.difficulty
        self.been_hit_this_level   = False
        self.been_seen_this_level  = False
        self.deaths_this_level     = 0
        self.kills_this_level      = 0

    def toggle_retro(
            self: Player,
    ) -> None:
        """Swap between the normal and retro sprite sets."""
        if self.is_retro:
            self.sprites  = self.sprites_set[0]
            self.is_retro = False
        else:
            self.sprites  = self.sprites_set[1] # noqa
            self.is_retro = True
        return None

    def save(
            self: Player,
    ) -> dict:
        """Return the actor's saved state plus the player's per-level statistics."""
        data = super().save()
        data[self.name].update({
            "been_hit_this_level":  self.been_hit_this_level,
            "been_seen_this_level": self.been_seen_this_level,
            "deaths_this_level":    self.deaths_this_level,
            "kills_this_level":     self.kills_this_level,
        })
        return data

    def load(
            self: Player,
            ent:  dict,
    ) -> None:
        """Restore the player's per-level statistics and base actor state."""
        self.load_attribute(ent, "been_hit_this_level")
        self.load_attribute(ent, "been_seen_this_level")
        self.load_attribute(ent, "deaths_this_level")
        self.load_attribute(ent, "kills_this_level")
        super().load(ent)
        return None

    def set_difficulty(
            self:  Player,
            scale: float,
    ) -> None:
        """Rescale the player's hp and damage inversely with difficulty."""
        self.difficulty     = scale
        self.max_hp         /= scale
        self.hp             /= scale
        self.attack_damage  /= scale
        return None

    def toggle_crouch(
            self: Player,
    ) -> None:
        """Toggle the player's crouch state."""
        self.is_crouching = not self.is_crouching
        return None

    def stop(
            self: Player,
    ) -> None:
        """Stop the player's horizontal movement."""
        self.should_move_horiz = False
        return None

    def block(
            self: Player,
    ) -> None:
        """Raise a temporary block shield if able and off cooldown."""
        if self.rect and self.abilities["can_block"] and self.cooldowns["block"] <= 0:
            self.cooldowns["blocking_effect"] = Player.BLOCK_EFFECT_TIME
            self.cooldowns["block"]           = Player.BLOCK_COOLDOWN
            scale = max(self.rect.width, self.rect.height)
            self.level.visual_effects_manager.spawn(
                VisualEffect(self, self.level.visual_effects_manager.image_master, image_name = "BLOCKSHIELD", alpha = 128, scale = (scale, scale), linked_to_source = True), # noqa
                time=Player.BLOCK_EFFECT_TIME,
            )
        return None

    def get_hit(
            self: Player,
            ent:  Entity,
    ) -> float:
        """Take a hit unless scrolling or blocking, applying rumble and returning the frame-time offset."""
        if self.controller.should_scroll_to_point is not None:
            return 0.0
        else:
            if isinstance(ent, NonPlayer) and self.cooldowns["blocking_effect"] > 0:
                self.cooldowns["blocking_effect"] = 0
                return 0.0
            else:
                self.been_hit_this_level = True
                if self.controller.gamepad is not None:
                    self.controller.gamepad.rumble(RUMBLE_EFFECT_LOW, RUMBLE_EFFECT_LOW, RUMBLE_EFFECT_DURATION)
                return super().get_hit(ent)

    def move_left(
            self: Player,
    ) -> None:
        """Begin moving the player left."""
        if self.hp > 0:
            self.should_move_horiz = True
            if self.direction != MovementDirection.LEFT:
                self.direction = self.facing = MovementDirection.LEFT
            if self.x_vel > 0:
                self.x_vel = 0
        return None

    def move_right(
            self: Player,
    ) -> None:
        """Begin moving the player right."""
        if self.hp > 0:
            self.should_move_horiz = True
            if self.direction != MovementDirection.RIGHT:
                self.direction = self.facing = MovementDirection.RIGHT
            if self.x_vel < 0:
                self.x_vel = 0
        return None

    def revert(
            self: Player,
    ) -> float:
        """Respawn the player at the cached state after death and return the frame-time offset."""
        start = time.perf_counter()
        text  = ["Careful!", "You died.", "Watch out!", "OUCH!", "Don't try that again!", "Initiating respawn...", "Reverting time..."]
        display_text(text[random.randrange(len(text))], self.controller, min_pause_time = 0, should_sleep = True, retro = self.level.retro)
        self.should_move_vert    = False
        self.rect.x, self.rect.y = int(self.cached_x), int(self.cached_y)
        self.hp                  = self.max_hp
        self.size                = self.cached_size
        self.size_target         = self.cached_size_target
        self.cooldowns           = self.cached_cooldowns
        self.cooldowns["dead"]   = 0.0
        self.deaths_this_level   += 1
        self.x_vel = self.y_vel  = 0.0
        return time.perf_counter() - start

    def teleport(
            self: Player,
    ) -> None:
        """Dash the player forward to the farthest unobstructed point within teleport range."""
        if self.rect and self.hp > 0 and self.abilities["can_teleport"] and self.cooldowns["teleport"] <= 0: # noqa
            for i in range(int(Player.VELOCITY_TARGET * Player.MULTIPLIER_TELEPORT) + 1, 0, -1):
                cast = Entity(self.level, self.controller, self.rect.x + (self.direction * i), self.rect.y, self.rect.width, self.rect.height - 1)
                if cast.rect:
                    if cast.rect.right <= self.level.level_bounds[0][0] or cast.rect.left >= self.level.level_bounds[1][0]:
                        collision = True
                    else:
                        collision = False
                        for ent in self.level.get_entities_in_range((cast.rect.x, cast.rect.y)):
                            if pygame.sprite.collide_rect(cast, ent): # noqa
                                collision = True
                                break
                    if not collision:
                        self.teleport_distance            = float(self.direction) * i
                        self.cooldowns["teleport_delay"]  = Player.TELEPORT_DELAY
                        self.cooldowns["teleport"]        = Player.TELEPORT_DELAY
                        return None
        return None

    def attack(
            self: Player,
    ) -> float:
        """Perform a melee attack, hitting hostile NPCs and breakable blocks, and return the frame-time offset."""
        dtime_offset: float = 0.0
        if self.rect and self.state in [MovementState.IDLE, MovementState.IDLE_CROUCH, MovementState.CROUCH, MovementState.RUN, MovementState.FALL, MovementState.JUMP, MovementState.DOUBLE_JUMP, MovementState.IDLE_ATTACK, MovementState.IDLE_CROUCH_ATTACK, MovementState.CROUCH_ATTACK, MovementState.RUN_ATTACK, MovementState.FALL_ATTACK, MovementState.JUMP_ATTACK, MovementState.DOUBLE_JUMP_ATTACK]:
            self.is_attacking = True
            for ent in self.level.get_entities_in_range((self.rect.x, self.rect.y)):
                if ent.rect:
                    if isinstance(ent, NonPlayer) and ent.is_hostile and pygame.sprite.collide_rect(self, ent) and self.facing == (MovementDirection.RIGHT if ent.rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT): # noqa
                        dtime_offset += ent.get_hit(self)
                        if ent.patrol_path is not None:
                            ent.push_x -= self.direction * int(Player.ATTACK_PUSHBACK)
                        self.play_attack_audio("ATTACK_MELEE")
                    elif isinstance(ent, BreakableBlock) and pygame.sprite.collide_rect(self, ent): # noqa
                        dtime_offset += ent.get_hit(self)
                        self.play_attack_audio("ATTACK_MELEE")
        return dtime_offset

    def bullet_time(
            self: Player,
    ) -> None:
        """Toggle bullet-time (slow motion) on or off if able and off cooldown."""
        if self.hp > 0 and self.abilities["can_bullet_time"]:
            if self.is_slow_time:
                self.is_slow_time                    = False
                self.cooldowns["bullet_time_active"] = 0
                self.cooldowns["bullet_time"]        = min(Player.BULLET_TIME_COOLDOWN, self.cooldowns["bullet_time"])
            elif self.cooldowns["bullet_time"] <= 0:
                self.is_slow_time                    = True
                self.cooldowns["bullet_time_active"] = Player.BULLET_TIME_ACTIVE
                self.cooldowns["bullet_time"]        = Player.BULLET_TIME_COOLDOWN
                if self.audios.get("BULLET_TIME") is not None:
                    active_audio_channel = pygame.mixer.find_channel()
                    if active_audio_channel is not None:
                        active_audio_channel.play(self.audios["BULLET_TIME"][random.randrange(len(self.audios["BULLET_TIME"]))])
                        active_audio_channel.set_volume(self.controller.master_volume["player"])
        return None

    def get_triggers(
            self: Player,
    ) -> float:
        """Fire any triggers the player overlaps, purging fire-once ones, and return the frame-time offset."""
        dtime_offset: float = 0.0
        for trigger in self.level.triggers:
            if pygame.sprite.collide_rect(self, trigger): # noqa
                dtime_offset += trigger.collide(self)
                if trigger.fire_once:
                    self.level.queue_purge(trigger)
        return dtime_offset

    def loop(
            self:  Player,
            dtime: float,
    ) -> float:
        """Advance the player for one frame, handling teleport, bullet time, and triggers."""
        dtime_offset: float = 0.0
        if self.teleport_distance != 0:
            self.animation_count += dtime
            if self.rect and self.cooldowns["teleport_delay"] <= 0:
                self.move(self.teleport_distance, 0)
                self.level.visual_effects_manager.spawn(
                    VisualEffect(
                        self,
                        self.level.visual_effects_manager.image_master, # noqa
                        image_name = "DASHCLOUD",
                        direction  = ImageDirection.RIGHT if self.facing == MovementDirection.RIGHT else ImageDirection.LEFT,
                        alpha      = 64,
                        offset     = (self.rect.width // 2, 0),
                        scale      = (abs(self.teleport_distance), self.rect.height * 0.8),
                    ),
                    time=Player.TELEPORT_EFFECT_TRAIL,
                )
                self.teleport_distance = 0
            self.update_cooldowns(dtime)
            self.update_state()
        else:
            if self.is_slow_time and self.cooldowns["bullet_time_active"] <= 0:
                self.is_slow_time = False
            dtime_offset += super().loop(dtime)
        return dtime_offset + self.get_triggers()
