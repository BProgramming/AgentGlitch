from __future__ import annotations
from typing import Any, TYPE_CHECKING
import math
import pygame
import random
from enum import Enum
from SimpleVFX.SimpleVFX import (
    VisualEffect,
    ImageDirection,
)

from Block import (
    Hazard,
    MovableBlock,
    MovingBlock,
)
from Entity import Entity
from Helpers import (
    MovementDirection,
    load_sprite_sheets,
    set_sound_source,
    RUMBLE_EFFECT_DURATION,
    RUMBLE_EFFECT_LOW,
    RUMBLE_EFFECT_HIGH,
)
from Objectives import Objective
from Projectile import Projectile

if TYPE_CHECKING:
    from Controller import Controller
    from Level import Level
# This file has lots of 'type: ignore' because PyCharm's type-checker can't validate when guards are nested multiple levels

class MovementState(Enum):
    IDLE               =  0
    RUN                =  1
    CROUCH             =  2
    JUMP               =  3
    DOUBLE_JUMP        =  4
    WALL_JUMP          =  5
    FALL               =  6
    HIT                =  7
    TELEPORT           =  8
    RESIZE             =  9
    SHOOT              = 10
    IDLE_ATTACK        = 11
    CROUCH_ATTACK      = 12
    RUN_ATTACK         = 13
    FALL_ATTACK        = 14
    JUMP_ATTACK        = 15
    DOUBLE_JUMP_ATTACK = 16
    WIND_UP            = 17
    ATTACK_ANIM        = 18
    WIND_DOWN          = 19
    IDLE_CROUCH        = 20
    IDLE_CROUCH_ATTACK = 21
    DEAD               = 22

    def __str__(self) -> str:
        return self.name


class Actor(Entity):
    SIZE:                  int =  64
    VELOCITY_TARGET:       int = 400
    VELOCITY_JUMP:         int = 500
    MIN_FALL_VEL:          int = 100
    MAX_SHOOT_DISTANCE:    int = 500
    HORIZ_PUSH_DECAY_RATE: int = 200
    ATTACK_DAMAGE:         int =  10

    GET_HIT_COOLDOWN:           float | int = 1.00
    LAUNCH_PROJECTILE_COOLDOWN: float | int = 1.00
    RESIZE_COOLDOWN:            float | int = 3.00
    RESIZE_DELAY:               float | int = 0.50
    RESIZE_SCALE_LIMIT:         float | int = 1.50
    RESIZE_EFFECT:              float | int = 0.05
    HEAL_DELAY:                 float | int = 5.00
    DOUBLEJUMP_EFFECT_TRAIL:    float | int = 0.08
    DEATH_TIME:                 float | int = 1.50
    BARK_TIME:                  float | int = 2.00

    def __init__(
            self:          Actor,
            level:         Level,
            controller:    Controller,
            x:             float | int,
            y:             float | int,
            sprite_master: dict[str, dict[str, list[pygame.Surface]]],
            audios:        dict[str, list[pygame.mixer.Sound]],
            difficulty:    float | int,
            block_size:    float | int,
            can_shoot:     bool        = False,
            can_resize:    bool        = False,
            width:         float | int = SIZE,
            height:        float | int = SIZE,
            attack_damage: float | int = ATTACK_DAMAGE,
            sprite:        str | None  = None,
            proj_sprite:   str | None  = None,
            name:          str         = "Actor",
    ):
        super().__init__(level, controller, x, y, width, height, name = name)
        self.difficulty: float | int = difficulty

        self.direction: MovementDirection = MovementDirection.RIGHT
        self.facing:    MovementDirection = MovementDirection.RIGHT

        self.is_hostile:    bool        = False
        self.is_attacking:  bool        = False
        self.attack_damage: float | int = attack_damage * difficulty

        self.abilities: dict[str, bool] = {
            "can_double_jump": False,
            "can_open_doors":  False,
            "can_move_blocks": False,
            "can_block":       False,
            "can_shoot":       can_shoot,
            "can_teleport":    False,
            "can_resize":      can_resize,
            "can_wall_jump":   False,
            "can_bullet_time": False,
            "can_heal":        False,
        }
        self.cooldowns.update(
            {
                "bark":                    0.0,
                "get_hit":                 0.0,
                "launch_projectile":       0.0,
                "resize":                  0.0,
                "resize_delay":            0.0,
                "resize_effect":           0.0,
                "heal":                    0.0,
                "attack":                  0.0,
                "doublejump_effect_trail": 0.0,
            }
        )
        self.cached_cooldowns: dict[str, float | int] = self.cooldowns.copy()

        self.patrol_path:       list[list[tuple[float | int, float | int] | bool]] | None = None
        self.x_vel:             float | int = 0.0
        self.y_vel:             float | int = 0.0
        self.x_accel_time:      float | int = 0.0
        self.x_accel_max_time:  float | int = 0.0
        self.target_vel:        float | int = Actor.VELOCITY_TARGET
        self.push_x:            float | int = 0.0
        self.push_y:            float | int = 0.0
        self.teleport_distance: float | int = 0.0
        self.should_move_horiz: bool        = False
        self.should_move_vert:  bool        = True
        self.is_crouching:      bool        = False
        self.is_wall_jumping:   bool        = False
        self.jump_count:        int         = 0

        self.state:               MovementState = MovementState.IDLE
        self.state_changed:       bool          = False
        self.idle_count:          int           = 0
        self.animation_count:     int           = 0
        self.is_final_anim_frame: bool          = False
        self.is_animated_attack:  bool          = False

        self.size:               float | int = 1.0
        self.size_target:        float | int = 1.0
        self.cached_size:        float | int = 1.0
        self.cached_size_target: float | int = 1.0

        self.sprite_name: str                             = sprite if sprite else "UnarmedAgent"
        self.sprites:     dict[str, list[pygame.Surface]] = load_sprite_sheets("Sprites", (sprite if sprite else "UnarmedAgent"), sprite_master, direction = True, retro = self.level.retro)
        self.sprite:      pygame.Surface | None           = None

        self.proj_sprite:        pygame.Surface | None = load_sprite_sheets("Projectiles", (proj_sprite if proj_sprite else "Bullet"), sprite_master, retro = self.level.retro)[(proj_sprite if proj_sprite else "Bullet").upper()][0]
        self.active_projectiles: list[Projectile]      = []

        self.audios:               dict[str, list[pygame.mixer.Sound]] = audios
        self.audio_trigger_frames: dict[str, list[int]]                = {
            "TELEPORT":    [0],
            "RUN":         [4, 10],
            "JUMP":        [0],
            "DOUBLE_JUMP": [0],
            "CROUCH":      [0],
            "HIT":         [0],
            "RESIZE":      [0],
        }
        self.active_audio:         pygame.mixer.Sound | None           = None
        self.active_audio_time:    float | int                         = 0.0
        self.active_audio_channel: pygame.mixer.Channel | None         = None

        self.update_sprite()
        self.update_geo()
        if self.rect:
            self.rect.x += (block_size - self.rect.width) // 2
            self.rect.y += (block_size - self.rect.height)
            self.cached_x: float | int = self.rect.x
            self.cached_y: float | int = self.rect.y

    @property
    def max_jumps(
            self: Actor,
    ) -> int:
        return 2 if self.abilities["can_double_jump"] else 1

    @property
    def gravity(
            self: Actor,
    ) -> float | int:
        return super().gravity * (self.size / (1 + (3 if self.is_wall_jumping and self.y_vel > 0 else 0)))

    def save(
            self: Actor,
    ) -> dict:
        projectiles = []
        for proj in self.active_projectiles:
            projectiles.append(proj.save())
        return {
            self.name: {
                "hp":          self.hp,
                "cached x y":  (self.cached_x, self.cached_y),
                "cooldowns":   self.cached_cooldowns,
                "size":        self.size,
                "size_target": self.size,
                "projectiles": projectiles,
            },
        }

    def load(
            self: Actor,
            data: dict[str, Any],
    ) -> None:
        self.rect.x, self.rect.y = self.cached_x, self.cached_y = data["cached x y"]

        self.cooldowns = self.cached_cooldowns = data["cooldowns"]

        self.load_attribute(data, "hp")
        self.load_attribute(data, "size")
        self.load_attribute(data, "size_target")

        for proj in data["projectiles"]:
            if self.rect:
                self.active_projectiles.append(
                    Projectile(
                        self.level,
                        self.controller,
                        self.rect.centerx + (self.rect.width * self.facing // 3),
                        self.rect.centery,
                        None,
                        0,
                        self.attack_damage,
                        self.difficulty,
                        sprite = self.proj_sprite,
                        name   = f"{self.name}'s projectile #{len(self.active_projectiles) + 1}",
                    ),
                )
            self.active_projectiles[-1].load(list(proj.values())[0])

        self.update_sprite()
        self.update_geo()

        return None

    def set_difficulty(
            self:  Actor,
            scale: float | int,
    ) -> None:
        self.difficulty = scale

        self.max_hp        *= scale
        self.hp            *= scale
        self.attack_damage *= scale

        for proj in self.active_projectiles:
            proj.set_difficulty(scale)
            proj.attack_damage = self.attack_damage

        return None

    def resize(
            self:   Actor,
            target: float | int,
    ) -> None:
        if self.hp > 0 and self.size_target != target:
            self.size_target               = target
            self.attack_damage             *= target
            self.cooldowns["resize"]       = Actor.RESIZE_DELAY
            self.cooldowns["resize_delay"] = Actor.RESIZE_DELAY

        return None

    def grow(
            self: Actor,
    ) -> None:
        if self.hp > 0 >= self.cooldowns["resize"] and self.abilities["can_resize"]:
            self.resize(min(self.size_target * Actor.RESIZE_SCALE_LIMIT, Actor.RESIZE_SCALE_LIMIT))
        return None

    def shrink(
            self: Actor,
    ) -> None:
        if self.hp > 0 >= self.cooldowns["resize"] and self.abilities["can_resize"]:
            self.resize(max(self.size_target / Actor.RESIZE_SCALE_LIMIT, 1 / Actor.RESIZE_SCALE_LIMIT))
        return None

    def move(
            self: Actor,
            dx: float | int,
            dy: float | int,
    ) -> None:
        if self.rect:
            if dx != 0:
                if self.rect.left + dx < self.level.level_bounds[0][0] - (self.rect.width // 5):
                    self.rect.left = -self.rect.width // 5
                elif self.rect.right + dx > self.level.level_bounds[1][0] + (self.rect.width // 5):
                    self.rect.right = self.level.level_bounds[1][0] + (self.rect.width // 5)
                else:
                    self.rect.x += dx

            if dy != 0:
                if self.rect.top + dy < self.level.level_bounds[0][1]:
                    self.hit_head()
                elif self.rect.top + dy > self.level.level_bounds[1][1]:
                    self.die()
                else:
                    self.rect.y += dy

        return None

    def cache(
            self: Actor,
    ) -> None:
        if (
                self.rect and
                self.cooldowns["get_hit"] <= 0 and
                self.state in (MovementState.IDLE, MovementState.IDLE_CROUCH, MovementState.RUN, MovementState.CROUCH) and
                self.hp         == self.max_hp and
                self.jump_count == 0 and
                self.y_vel      == 0
        ):
            self.cached_x, self.cached_y = self.rect.x, self.rect.y
            self.cached_size        = self.size
            self.cached_size_target = self.size_target
            self.cached_cooldowns   = self.cooldowns.copy()

        return None

    def revert(
            self: Actor,
    ) -> int:
        return 0

    def jump(
            self: Actor,
    ) -> None:
        if self.rect and self.hp > 0 and self.jump_count < self.max_jumps:
            self.should_move_vert = True
            self.y_vel            = -Actor.VELOCITY_JUMP
            self.jump_count       += 1

            if self.jump_count > 1:
                rotation = (self.x_vel / self.y_vel) * 30
                self.level.visual_effects_manager.spawn(
                    VisualEffect(
                        self,
                        self.level.visual_effects_manager.image_master,
                        image_name = "JUMPLINES",
                        direction  = [ImageDirection.BOTTOM, (ImageDirection.RIGHT if self.facing == MovementDirection.RIGHT else ImageDirection.LEFT)],
                        rotation   = rotation,
                        alpha      = 64,
                        offset     = (self.rect.width // 2, 0),
                        scale      = (self.rect.width // 2, self.rect.height),
                    ),
                    time = Actor.DOUBLEJUMP_EFFECT_TRAIL,
                )

            if self.is_wall_jumping:
                self.is_wall_jumping = False
                self.direction       = self.direction.swap()
                self.facing          = self.facing.swap()
                self.move(self.direction * self.rect.width // 4, 0)

        self.is_crouching = False

        return None

    def land(
            self: Actor,
    ) -> None:
        self.should_move_vert = False

        if self.y_vel > 2 * Actor.VELOCITY_JUMP:
            self.hp -= self.y_vel * self.y_vel / (18000 * self.size)
            if self.hp < 0:
                self.die()
            elif self == self.level.player and self.controller.gamepad is not None:
                self.controller.gamepad.rumble(RUMBLE_EFFECT_LOW, RUMBLE_EFFECT_LOW, RUMBLE_EFFECT_DURATION)

        self.y_vel           = 0.0
        self.jump_count      = 0
        self.is_wall_jumping = False

        return None

    def hit_head(
            self: Actor,
    ) -> None:
        self.y_vel *= -0.5
        return None

    def play_attack_audio(
            self:        Actor,
            attack_type: str,
    ) -> None:
        if attack_type in self.audios:
            active_audio_channel = pygame.mixer.find_channel()

            if active_audio_channel is not None:
                active_audio_channel.play(self.audios[attack_type][random.randrange(len(self.audios[attack_type]))])

                if self == self.level.player:
                    active_audio_channel.set_volume(self.controller.master_volume["player"])
                else:
                    set_sound_source(self.rect, self.level.player.rect, self.controller.master_volume["non-player"], active_audio_channel)

        return None

    def shoot_at_target(
            self:   Actor,
            target: tuple[int, int],
    ) -> None:
        if self.rect and self.hp > 0 >= self.cooldowns["launch_projectile"]:
            adj_target = target[0], self.rect.centery
            proj = Projectile(
                self.level,
                self.controller,
                self.rect.centerx,
                self.rect.centery,
                adj_target,
                Actor.MAX_SHOOT_DISTANCE,
                self.attack_damage,
                self.difficulty,
                sprite = self.proj_sprite,
                name   = f"{self.name}'s projectile #{(len(self.active_projectiles) + 1)}"
            )
            self.active_projectiles.append(proj)

            self.is_attacking                   = True
            self.cooldowns["launch_projectile"] = Actor.LAUNCH_PROJECTILE_COOLDOWN
            self.play_attack_audio("ATTACK_RANGE")

        return None

    def get_hit(
            self: Actor,
            ent:  Entity,
    ) -> float | int:
        self.cooldowns["get_hit"] = Actor.GET_HIT_COOLDOWN
        self.cooldowns["heal"]    = Actor.HEAL_DELAY * self.difficulty

        if ent.attack_damage is not None:
            self.hp -= ent.attack_damage
            if self.hp < 0:
                self.die()

        return 0.0

    def get_collisions(
            self: Actor,
    ) -> float | int:
        if not self.rect:
            return 0.0

        collided = False
        dtime_offset: float | int = 0.0

        if self == self.level.player:
            ents = self.level.get_entities_in_range((self.rect.x, self.rect.y)) # type: ignore
        elif self.is_hostile:
            ents = [self.level.player] + self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only = True, include_doors = True) # type: ignore
        else:
            ents = self.level.get_entities_in_range((self.rect.x, self.rect.y), blocks_only = True, include_doors = True) # type: ignore

        for ent in ents:
            if ent.rect and ent.mask and self.rect.colliderect(ent.rect): # type: ignore
                if pygame.sprite.collide_mask(self, ent): # type: ignore
                    if isinstance(ent, Actor) or isinstance(ent, Objective):
                        overlap = self.mask.overlap_mask(ent.mask, (0, 0)).get_rect() # type: ignore
                    else:
                        overlap = self.rect.clip(ent.rect) # type: ignore

                    if isinstance(ent, Actor) and ent != self.level.player:
                        if ent.facing == (MovementDirection.RIGHT if self.rect.centerx - ent.rect.centerx >= 0 else MovementDirection.LEFT) and ent.is_attacking and self.cooldowns["get_hit"] <= 0: # type: ignore
                            dtime_offset += self.get_hit(ent)
                    elif isinstance(ent, Hazard):
                        if ent.is_attacking and self.cooldowns["get_hit"] <= 0:
                            if overlap.width <= overlap.height and ((self.rect.x <= ent.rect.x and "L" in ent.hit_sides) or (self.rect.x >= ent.rect.x and "R" in ent.hit_sides)): # type: ignore
                                dtime_offset += self.get_hit(ent)

                            if overlap.width >= overlap.height and ((self.rect.y <= ent.rect.y and "U" in ent.hit_sides) or (self.rect.y >= ent.rect.y and "D" in ent.hit_sides)): # type: ignore
                                dtime_offset += self.get_hit(ent)
                    elif isinstance(ent, Objective) and self == self.level.player:
                        dtime_offset += ent.get_hit(self)

                    if ent.collide(self):
                        self.collide(ent)
                        if overlap.width <= overlap.height and (self.x_vel == 0 or self.direction == (MovementDirection.RIGHT if self.x_vel >= 0 else MovementDirection.LEFT)):
                            if self.abilities["can_move_blocks"] and isinstance(ent, MovableBlock) and ent.should_move_horiz and self.direction == (MovementDirection.RIGHT if ent.rect.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT): # type: ignore
                                ent.push_x = self.x_vel * self.size

                            if (isinstance(ent, Actor) and ent.is_hostile) or not isinstance(ent, Actor):
                                if self.x_vel <= 0 and self.rect.centerx > ent.rect.centerx: # type: ignore
                                    self.rect.left = ent.rect.right - (self.rect.width // 5) # type: ignore
                                    self.x_vel     = 0.0
                                elif self.x_vel >= 0 and self.rect.centerx <= ent.rect.centerx: # type: ignore
                                    self.rect.right = ent.rect.left + (self.rect.width // 5) # type: ignore
                                    self.x_vel      = 0.0

                            collided = True

                        if overlap.width >= overlap.height:
                            if self.y_vel >= 0 and not ent.is_stacked and self.rect.bottom == overlap.bottom: # type: ignore
                                self.rect.bottom = ent.rect.top # type: ignore
                                self.land()
                            elif self.y_vel < 0 and self.rect.top == overlap.top: # type: ignore
                                self.rect.top = ent.rect.bottom # type: ignore
                                self.hit_head()

                        if collided and self.should_move_vert and self.abilities["can_wall_jump"] and not self.is_wall_jumping and self.direction == (MovementDirection.RIGHT if overlap.centerx - self.rect.centerx >= 0 else MovementDirection.LEFT): # type: ignore
                            self.y_vel           = min(self.y_vel, 0.0)
                            self.jump_count      = 0
                            self.is_wall_jumping = True
                elif isinstance(ent, Objective) and self == self.level.player and ent.sprite is None:
                    dtime_offset += ent.get_hit(self)
            elif ent.rect.top <= self.rect.bottom <= ent.rect.bottom and self.rect.left + (self.rect.width // 4) <= ent.rect.right and self.rect.right - (self.rect.width // 4) >= ent.rect.left: # type: ignore
                if isinstance(ent, MovingBlock) or isinstance(ent, MovableBlock) :
                    ent.collide(self)

                if self.rect.centerx != ent.rect.centerx: # type: ignore
                    if math.degrees(math.atan(abs(self.rect.centery - ent.rect.centery) / abs(self.rect.centerx - ent.rect.centerx))) >= 45: # type: ignore
                        self.should_move_vert = False

                        if self.rect.bottom != ent.rect.top: # type: ignore
                            self.rect.bottom = ent.rect.top # type: ignore

        if self.y_vel != 0 and not collided and self.is_wall_jumping:
            if self.direction == MovementDirection.RIGHT:
                dist_x = (0, 1)
            else:
                dist_x = (1, 0)

            check_blocks = len(self.level.get_entities_in_range((self.rect.x, self.rect.y), dist_x = dist_x, blocks_only = True, include_doors = False)) # type: ignore

            if check_blocks == 0:
                self.is_wall_jumping = False

        return dtime_offset

    def die(
            self: Actor,
    ) -> None:
        super().die()

        if self.hp <= 0 and self.cooldowns.get('dead') and self.cooldowns['dead'] <= 0:
            self.cooldowns['dead'] = Actor.DEATH_TIME

            if self == self.level.player and self.controller.gamepad:
                self.controller.gamepad.rumble(RUMBLE_EFFECT_HIGH, RUMBLE_EFFECT_HIGH, RUMBLE_EFFECT_DURATION)

        return None

    def update_state(
            self: Actor,
    ) -> None:
        old = self.state
        if self.hp <= 0 and self.cooldowns.get('dead') is not None:
            if self.state != MovementState.DEAD:
                self.state           = MovementState.DEAD
                self.animation_count = 0
        elif self.size_target != self.size:
            # this is not combined because, when kept separate, it lets the animation keep playing until the cooldown ends
            if self.state != MovementState.RESIZE:
                self.state           = MovementState.RESIZE
                self.animation_count = 0
        # this is for boss enemies with complex attack animations
        elif self.is_animated_attack and self.is_attacking:
            if self.state not in [MovementState.WIND_UP, MovementState.ATTACK_ANIM, MovementState.WIND_DOWN]:
                self.state           = MovementState.WIND_UP
                self.animation_count = 0
            elif self.is_final_anim_frame:
                if self.state == MovementState.WIND_UP:
                    self.state           = MovementState.ATTACK_ANIM
                    self.animation_count = 0
                elif self.state == MovementState.ATTACK_ANIM:
                    self.state           = MovementState.WIND_DOWN
                    self.animation_count = 0
                else:
                    self.is_attacking = False
                    self.update_state()
                    return None
        elif self.cooldowns["get_hit"] > 0:
            # this is not combined because, when kept separate, it lets the animation keep playing until the cooldown ends
            if self.state != MovementState.HIT:
                self.state           = MovementState.HIT
                self.animation_count = 0
        else:
            if self.teleport_distance != 0:
            # this is not combined because, when kept separate, it lets the animation keep playing until the cooldown ends
                if self.state != MovementState.TELEPORT:
                    self.state           = MovementState.TELEPORT
                    self.animation_count = 0
            elif self.should_move_vert and (self.is_wall_jumping or self.y_vel > Actor.MIN_FALL_VEL or self.y_vel < 0):
                if self.abilities["can_wall_jump"] and self.is_wall_jumping:
                    if self.state != MovementState.WALL_JUMP:
                        self.state           = MovementState.WALL_JUMP
                        self.animation_count = 0
                elif self.y_vel > Actor.MIN_FALL_VEL:
                    if self.is_attacking and self.state != MovementState.FALL_ATTACK:
                        if self.state != MovementState.FALL:
                            self.animation_count = 0
                        self.state = MovementState.FALL_ATTACK
                    elif not self.is_attacking and self.state != MovementState.FALL:
                        if self.state != MovementState.FALL_ATTACK:
                            self.animation_count = 0
                        self.state = MovementState.FALL
                elif self.jump_count > 1:
                    if self.is_attacking and self.state != MovementState.DOUBLE_JUMP_ATTACK:
                        if self.state != MovementState.DOUBLE_JUMP:
                            self.animation_count = 0
                        self.state = MovementState.DOUBLE_JUMP_ATTACK
                    elif not self.is_attacking and self.state != MovementState.DOUBLE_JUMP:
                        if self.state != MovementState.DOUBLE_JUMP_ATTACK:
                            self.animation_count = 0
                        self.state = MovementState.DOUBLE_JUMP
                else:
                    if self.is_attacking and self.state != MovementState.JUMP_ATTACK:
                        if self.state != MovementState.JUMP:
                            self.animation_count = 0
                        self.state = MovementState.JUMP_ATTACK
                    elif not self.is_attacking and self.state != MovementState.JUMP:
                        if self.state != MovementState.JUMP_ATTACK:
                            self.animation_count = 0
                        self.state = MovementState.JUMP
            elif self.should_move_horiz:
                if self.is_crouching:
                    if self.is_attacking and self.state != MovementState.CROUCH_ATTACK:
                        if self.state != MovementState.CROUCH:
                            self.animation_count = 0
                        self.state = MovementState.CROUCH_ATTACK
                    elif not self.is_attacking and self.state != MovementState.CROUCH:
                        if self.state != MovementState.CROUCH_ATTACK:
                            self.animation_count = 0
                        self.state = MovementState.CROUCH
                else:
                    if self.is_attacking and self.state != MovementState.RUN_ATTACK:
                        if self.state != MovementState.RUN:
                            self.animation_count = 0
                        self.state = MovementState.RUN_ATTACK
                    elif not self.is_attacking and self.state != MovementState.RUN:
                        if self.state != MovementState.RUN_ATTACK:
                            self.animation_count = 0
                        self.state = MovementState.RUN
            else:
                if self.is_crouching:
                    if self.is_attacking and self.state != MovementState.IDLE_CROUCH_ATTACK:
                        if self.state not in (MovementState.IDLE, MovementState.IDLE_ATTACK, MovementState.IDLE_CROUCH, MovementState.IDLE_CROUCH_ATTACK):
                            self.animation_count = 0
                        self.state = MovementState.IDLE_CROUCH_ATTACK
                    elif not self.is_attacking and self.state != MovementState.IDLE_CROUCH:
                        if self.state not in (MovementState.IDLE, MovementState.IDLE_ATTACK, MovementState.IDLE_CROUCH, MovementState.IDLE_CROUCH_ATTACK):
                            self.animation_count = 0
                        self.state = MovementState.IDLE_CROUCH
                else:
                    if self.is_attacking and self.state != MovementState.IDLE_ATTACK:
                        if self.state not in (MovementState.IDLE, MovementState.IDLE_ATTACK, MovementState.IDLE_CROUCH, MovementState.IDLE_CROUCH_ATTACK):
                            self.animation_count = 0
                        self.state = MovementState.IDLE_ATTACK
                    elif not self.is_attacking and self.state != MovementState.IDLE:
                        if self.state not in (MovementState.IDLE, MovementState.IDLE_ATTACK, MovementState.IDLE_CROUCH, MovementState.IDLE_CROUCH_ATTACK):
                            self.animation_count = 0
                        self.state = MovementState.IDLE

            if f"{str(self.state)}_{str(self.facing)}" not in self.sprites:
                self.state = old

        self.state_changed = bool(old != self.state)

        return None

    def update_sprite(
            self: Actor,
    ) -> int:
        active_sprites = self.sprites[f"{str(self.state)}_{str(self.facing)}"]
        active_index   = math.floor((self.animation_count / Actor.ANIMATION_DELAY) % len(active_sprites))

        if active_index == len(active_sprites) - 1:
            self.is_final_anim_frame = True
        else:
            self.is_final_anim_frame = False

            if active_index >= len(active_sprites):
                active_index         = 0
                self.animation_count = 0

        self.sprite = active_sprites[active_index]
        if self.sprite and self.size != 1:
            self.sprite = pygame.transform.smoothscale_by(self.sprite, self.size)

        if self.audios is not None and (self.state_changed or self.state == MovementState.RUN) and self.audio_trigger_frames.get(str(self.state)) is not None:
            if self.audios.get(str(self.state).replace("_ATTACK", "")) is not None and active_index in self.audio_trigger_frames[str(self.state).replace("_ATTACK", "")]:
                self.active_audio = self.audios[str(self.state).replace("_ATTACK", "")][random.randrange(len(self.audios[str(self.state).replace("_ATTACK", "")]))]

                if self.active_audio_channel is not None:
                    self.active_audio_channel.stop()
                    self.active_audio_channel = None

        return active_index

    def update_geo(
            self: Actor,
    ) -> None:
        if self.sprite and self.rect:
            self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
            self.mask = pygame.mask.from_surface(self.sprite)
        return None

    def loop(
            self:  Actor,
            dtime: float | int,
    ) -> float:
        dtime_offset: float | int = super().loop(dtime)

        self.animation_count += dtime

        if self.abilities["can_heal"] and self.hp < self.max_hp and self.cooldowns["heal"] <= 0:
            self.hp = min(self.max_hp, self.hp + ((self.max_hp * dtime) / (50 * self.difficulty)))

        if len(self.active_projectiles) > 0:
            for proj in self.active_projectiles:
                if proj.hp <= 0:
                    self.active_projectiles.remove(proj)
                else:
                    dtime_offset += proj.loop(dtime)

        if (self == self.level.player or self.patrol_path is not None) and self.state != MovementState.WIND_UP and self.state != MovementState.WIND_DOWN:
            if self.push_x > 0:
                self.push_x = max(self.push_x - (Actor.HORIZ_PUSH_DECAY_RATE * dtime), 0)
            elif self.push_x < 0:
                self.push_x = min(self.push_x + (Actor.HORIZ_PUSH_DECAY_RATE * dtime), 0)

            self.push_y           = 0
            self.should_move_vert = True

            dtime_offset += self.get_collisions()

            if self.rect and self.cooldowns["resize_delay"] <= 0:
                if self.size != self.size_target:
                    if self.size > self.size_target:
                        self.rect.y += self.rect.height // 3
                    else:
                        self.rect.y -= self.rect.height // 2

                    scale_factor = self.size_target * 1.25

                    if self.size_target == 1:
                        if self.size < self.size_target:
                            scale_factor *= 1.5
                        else:
                            scale_factor /= 1.5

                    self.size = self.size_target

                    self.level.visual_effects_manager.spawn(
                        VisualEffect(
                            self,
                            self.level.visual_effects_manager.image_master,
                            image_name       = "RESIZEBURST",
                            alpha            = 128,
                            scale            = (self.rect.width * scale_factor, self.rect.height * scale_factor),
                            linked_to_source = True,
                        ),
                        time = Actor.RESIZE_EFFECT,
                    )

                if self.should_move_horiz:
                    if self.x_accel_time < self.x_accel_max_time and abs(self.x_vel) < self.target_vel:
                        self.x_accel_time += dtime
                        self.x_vel = self.direction * self.target_vel * math.sqrt(self.x_accel_time / self.x_accel_max_time)
                    else:
                        self.x_vel = self.direction * self.target_vel
                else:
                    self.x_accel_time = 0.0
                    self.x_vel        = 0.0

                if self.should_move_vert:
                    self.y_vel += self.gravity * dtime

                if self.x_vel + self.push_x != 0 or self.y_vel + self.push_y != 0:
                    if self.level.player.is_slow_time and self != self.level.player:
                        self.x_vel /= 2
                        self.y_vel /= 2

                    if self.state in (MovementState.CROUCH, MovementState.CROUCH_ATTACK, MovementState.IDLE_CROUCH, MovementState.IDLE_CROUCH_ATTACK):
                        self.x_vel *= 0.75

                    self.move((self.x_vel + self.push_x) * dtime, (self.y_vel + self.push_y) * dtime)
            else:
                self.move(self.push_x * dtime, self.push_y * dtime)

        self.cache()
        self.update_state()

        return dtime_offset

    def draw(
            self:          Actor,
            win:           pygame.Surface,
            offset_x:      float | int,
            offset_y:      float | int,
            master_volume: dict[str, float | int],
    ) -> None:
        adj_x_image   = self.rect.x - offset_x # type: ignore
        adj_y_image   = self.rect.y - offset_y # type: ignore
        window_width  = win.get_width()
        window_height = win.get_height()

        if len(self.active_projectiles) > 0:
            for proj in self.active_projectiles:
                proj.draw(win, offset_x, offset_y, master_volume)

        if self.sprite and self.rect and -self.rect.width < adj_x_image <= window_width and -self.rect.height < adj_y_image <= window_height:
            self.update_sprite()
            self.update_geo()

            win.blit(self.sprite, (adj_x_image, adj_y_image))

        if self.active_audio:
            if not self.active_audio_channel:
                self.active_audio_channel = pygame.mixer.find_channel()

                if self.active_audio_channel:
                    self.active_audio_channel.play(self.active_audio)

            if self.active_audio_channel and self.active_audio_channel.get_busy():
                if self == self.level.player:
                    self.active_audio_channel.set_volume(master_volume["player"]) # type: ignore
                else:
                    set_sound_source(self.rect, self.level.player.rect, self.controller.master_volume["non-player"], self.active_audio_channel)
            else:
                self.active_audio         = None
                self.active_audio_channel = None

        return None
